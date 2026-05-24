from __future__ import annotations

import time

from ..constants import Ids
from ..errors import UiElementNotFound
from ..models import Message, SendResult


class ChatPage:
    def __init__(self, account):
        self.account = account
        self.device = account.device

    def title(self) -> str | None:
        tree = self.device.dump_tree()
        node = tree.find_by_id(Ids.TITLE)
        return node.text if node else None

    def send_text(self, target: str, text: str, *, verify: bool = True) -> SendResult:
        if not self.device.execute:
            self.device.audit.record("dry_run_send_message", target=target, text=text)
            return SendResult(target=target, text=text, sent=False, dry_run=True, detail="dry-run")

        with self.device.adb_keyboard():
            tree = self.device.dump_tree()
            input_node = tree.find_by_id(Ids.CHAT_INPUT)
            if input_node is None:
                raise UiElementNotFound(Ids.CHAT_INPUT)
            self.device.tap(input_node, description="focus chat input")
            self.device.input_text(text, clear=True, mutating=True)

            typed_tree = self.device.dump_tree()
            send_button = typed_tree.find_by_id(Ids.CHAT_SEND)
            if send_button is None:
                raise UiElementNotFound(Ids.CHAT_SEND)
            self.device.tap(send_button, description=f"send message to {target}", mutating=True)
            time.sleep(1.2)

        verified = False
        if verify:
            sent_tree = self.device.dump_tree()
            verified = any(node.text == text for node in sent_tree.find_all_by_id(Ids.CHAT_CONTENT))
        self.device.audit.record("send_message", target=target, text=text, verified=verified)
        return SendResult(target=target, text=text, sent=True, verified=verified)

    def read_history(self, limit: int | None = 50, *, max_pages: int = 1) -> list[Message]:
        history: list[Message] = []
        previous_signature: tuple[tuple[str, str, str | None], ...] | None = None
        stable_pages = 0

        for page_index in range(max_pages):
            tree = self.device.dump_tree()
            page_messages = self._parse_visible_messages(tree)
            history = (
                page_messages
                if page_index == 0
                else self._merge_older_page(history, page_messages)
            )

            signature = tuple(self._message_key(message) for message in page_messages)
            if signature == previous_signature:
                stable_pages += 1
                if stable_pages >= 2:
                    break
            else:
                stable_pages = 0
            previous_signature = signature

            if page_index < max_pages - 1:
                self.device.swipe(
                    (600, 900),
                    (600, 2200),
                    duration_ms=650,
                    description="scroll chat history older",
                )
                time.sleep(0.8)

        return history[-limit:] if limit is not None else history

    def _parse_visible_messages(self, tree) -> list[Message]:
        content_nodes = tree.find_all_by_id(Ids.CHAT_CONTENT)
        messages: list[Message] = []
        screen_mid_x = self._screen_mid_x(tree)
        for node in content_nodes:
            direction = "unknown"
            bubble = node.parent
            if bubble is not None:
                center_x, _ = bubble.center
                direction = "outgoing" if center_x > screen_mid_x else "incoming"
            messages.append(Message(text=node.text, direction=direction))
        return messages

    def _screen_mid_x(self, tree) -> int:
        right = 0
        for node in tree.walk():
            try:
                right = max(right, node.bounds.right)
            except ValueError:
                continue
        return right // 2 if right else 600

    @staticmethod
    def _message_key(message: Message) -> tuple[str, str, str | None]:
        return (message.direction, message.text, message.timestamp)

    @classmethod
    def _merge_older_page(
        cls,
        current: list[Message],
        older_page: list[Message],
    ) -> list[Message]:
        if not current:
            return older_page
        if not older_page:
            return current

        current_keys = [cls._message_key(message) for message in current]
        older_keys = [cls._message_key(message) for message in older_page]
        max_overlap = min(len(current_keys), len(older_keys))

        for size in range(max_overlap, 0, -1):
            if older_keys[-size:] == current_keys[:size]:
                return older_page[:-size] + current
        return older_page + current

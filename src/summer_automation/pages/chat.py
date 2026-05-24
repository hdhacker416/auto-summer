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

    def read_history(self, limit: int = 50) -> list[Message]:
        tree = self.device.dump_tree()
        content_nodes = tree.find_all_by_id(Ids.CHAT_CONTENT)
        messages: list[Message] = []
        for node in content_nodes[-limit:]:
            direction = "unknown"
            bubble = node.parent
            if bubble is not None:
                center_x, _ = bubble.center
                direction = "outgoing" if center_x > 600 else "incoming"
            messages.append(Message(text=node.text, direction=direction))
        return messages

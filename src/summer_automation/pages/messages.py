from __future__ import annotations

from ..constants import Ids
from ..errors import UiElementNotFound
from ..models import Friend, Message, SendResult


class MessagesPage:
    DEFAULT_SKIP_NAMES: set[str] = {"Summer小秘书", "收到答卷", "答题记录"}
    DEFAULT_SKIP_KEYWORDS: tuple[str, ...] = ("收到答卷", "答题记录")

    def __init__(self, account):
        self.account = account
        self.device = account.device

    def open(self) -> None:
        self.account.main.open_tab("消息")

    def list_recent_chats(
        self,
        *,
        limit: int | None = None,
        skip_names: set[str] | None = None,
        open_tab: bool = True,
    ) -> list[Friend]:
        if open_tab:
            self.open()
        tree = self.device.dump_tree()
        skip = self.DEFAULT_SKIP_NAMES | (skip_names or set())
        friends: list[Friend] = []
        for node in tree.find_all_by_id(Ids.MESSAGE_NICKNAME):
            if self._should_skip_chat(node.text, skip):
                continue
            row = node.clickable_ancestor()
            preview = row.find_descendant_by_id(Ids.MESSAGE_PREVIEW)
            friend = Friend(
                nickname=node.text,
                account=self.account,
                source="messages",
                row_bounds=row.bounds,
                bio=preview.text if preview else None,
            )
            friends.append(friend)
            if limit is not None and len(friends) >= limit:
                break
        return friends

    def _should_skip_chat(self, nickname: str, skip_names: set[str]) -> bool:
        if not nickname or nickname in skip_names:
            return True
        return any(keyword in nickname for keyword in self.DEFAULT_SKIP_KEYWORDS)

    def _tap_friend_row(self, friend: Friend) -> None:
        self.open()
        tree = self.device.dump_tree()
        for node in tree.find_all_by_id(Ids.MESSAGE_NICKNAME):
            if node.text == friend.nickname:
                self.device.tap(node.clickable_ancestor(), description=f"open chat {friend.nickname}")
                return
        if friend.row_bounds is not None:
            x, y = friend.row_bounds.center
            self.device.tap(x, y, description=f"open chat {friend.nickname} from saved bounds")
            return
        raise UiElementNotFound(f"chat row for {friend.nickname}")

    def open_chat(self, friend: Friend) -> None:
        self._tap_friend_row(friend)
        self.device.wait_for(
            lambda: "ChatActivity" in self.device.current_focus(),
            description="ChatActivity",
        )

    def send_message(self, friend: Friend, text: str) -> SendResult:
        self.open_chat(friend)
        return self.account.chat.send_text(friend.nickname, text)

    def read_history(
        self,
        friend: Friend,
        *,
        limit: int | None = 50,
        max_pages: int = 1,
    ) -> list[Message]:
        self.open_chat(friend)
        return self.account.chat.read_history(limit=limit, max_pages=max_pages)

    def receive_messages(
        self,
        friend: Friend,
        *,
        since: str | None = None,
        limit: int | None = 50,
        max_pages: int = 1,
    ) -> list[Message]:
        messages = self.read_history(friend, limit=limit, max_pages=max_pages)
        if since is None:
            return messages
        return [message for message in messages if message.timestamp and message.timestamp > since]

    def send_to_top_conversations(
        self,
        text: str,
        *,
        limit: int = 5,
        skip_names: set[str] | None = None,
    ) -> list[SendResult]:
        self.device.safety.check_batch(limit)
        friends = self.list_recent_chats(limit=limit, skip_names=skip_names)
        results: list[SendResult] = []
        for friend in friends:
            result = self.send_message(friend, text)
            results.append(result)
            self.account.main.ensure_main()
        return results

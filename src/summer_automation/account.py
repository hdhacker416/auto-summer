from __future__ import annotations

from pathlib import Path

from .constants import PACKAGE_NAME
from .device import AndroidDevice
from .models import Friend, Stranger
from .pages.chat import ChatPage
from .pages.main import MainPage
from .pages.messages import MessagesPage
from .pages.paper import PaperPage
from .pages.strangers import StrangersPage


class SummerAccount:
    """High-level automation object for one logged-in Summer account."""

    def __init__(
        self,
        serial: str | None = None,
        *,
        execute: bool = False,
        adb_path: str = "adb",
        package_name: str = PACKAGE_NAME,
        max_batch: int = 5,
        audit_log: str | Path | None = None,
        log_message_content: bool = False,
    ):
        self.device = AndroidDevice(
            serial=serial,
            adb_path=adb_path,
            package_name=package_name,
            execute=execute,
            max_batch=max_batch,
            audit_log=audit_log,
            log_message_content=log_message_content,
        )
        self.main = MainPage(self)
        self.messages = MessagesPage(self)
        self.chat = ChatPage(self)
        self.strangers = StrangersPage(self)
        self.paper = PaperPage(self)

    def __enter__(self) -> "SummerAccount":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        previous = self.device._previous_ime
        if previous and previous != self.device.get_default_ime():
            self.device.set_ime(previous)

    def input_text(self, text: str, *, clear: bool = True) -> bool:
        """Input text into the currently focused field on the phone.

        This is useful when a tester manually navigates to a field and wants the
        SDK to handle reliable Chinese input only.
        """
        with self.device.adb_keyboard():
            return self.device.input_text(text, clear=clear, mutating=True)

    def get_friend_list(
        self,
        *,
        limit: int | None = None,
        source: str = "messages",
        skip_names: set[str] | None = None,
    ) -> list[Friend]:
        """Return friend-like objects.

        The first implementation uses the recent message list because it is the
        most stable tested surface. If the current screen is already a friend
        list, use `source="current"` to parse visible friend rows directly.
        """
        if source in {"messages", "recent"}:
            return self.messages.list_recent_chats(limit=limit, skip_names=skip_names)
        if source == "current":
            tree = self.device.dump_tree()
            friends: list[Friend] = []
            for node in tree.find_all_by_id("cn.imsummer.summer:id/nearby_user_item_nickname"):
                row = node.clickable_ancestor()
                friends.append(
                    Friend(
                        nickname=node.text,
                        account=self,
                        source="current",
                        row_bounds=row.bounds,
                    )
                )
                if limit is not None and len(friends) >= limit:
                    break
            return friends
        raise ValueError(f"Unsupported friend source: {source}")

    def get_stranger_list(self, *, limit: int | None = None) -> list[Stranger]:
        return self.strangers.list_visible(limit=limit)

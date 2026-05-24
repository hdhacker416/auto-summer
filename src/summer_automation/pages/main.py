from __future__ import annotations

import time

from ..constants import Ids
from ..errors import UiElementNotFound


class MainPage:
    def __init__(self, account):
        self.account = account
        self.device = account.device

    def ensure_main(self, *, max_back: int = 4) -> None:
        focus = self.device.current_focus()
        if "MainActivity" in focus:
            return
        for _ in range(max_back):
            self.device.back()
            focus = self.device.current_focus()
            if "MainActivity" in focus:
                return
        self.device.launch()

    def open_tab(self, label: str) -> None:
        self.ensure_main()
        tree = self.device.dump_tree()
        labels = tree.find_all(lambda node: node.resource_id == Ids.MAIN_TAB_LABEL and node.text == label)
        if not labels:
            raise UiElementNotFound(f"bottom tab {label!r}")
        target = labels[-1].clickable_ancestor()
        self.device.tap(target, description=f"open tab {label}")
        time.sleep(1)

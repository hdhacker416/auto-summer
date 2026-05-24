from __future__ import annotations

import base64
import time
from contextlib import contextmanager
from pathlib import Path

from .adb import Adb
from .constants import ADB_KEYBOARD_IME, PACKAGE_NAME
from .errors import AppStateError, UiElementNotFound
from .safety import AuditLogger, SafetyConfig
from .ui_tree import UiNode, UiTree


class AndroidDevice:
    def __init__(
        self,
        serial: str | None = None,
        *,
        adb_path: str = "adb",
        package_name: str = PACKAGE_NAME,
        execute: bool = False,
        max_batch: int = 5,
        audit_log: str | Path | None = None,
        log_message_content: bool = False,
        timeout: int = 20,
    ):
        self.adb = Adb(serial=serial, adb_path=adb_path, timeout=timeout)
        self.package_name = package_name
        self.safety = SafetyConfig(
            execute=execute,
            max_batch=max_batch,
            package_name=package_name,
            audit_log=Path(audit_log) if audit_log else None,
            log_message_content=log_message_content,
        )
        self.audit = AuditLogger(
            self.safety.audit_log,
            log_message_content=self.safety.log_message_content,
        )
        self._previous_ime: str | None = None

    @property
    def execute(self) -> bool:
        return self.safety.execute

    def current_focus(self) -> str:
        output = self.adb.run("shell", "dumpsys", "window", timeout=30)
        lines = [line.strip() for line in output.splitlines() if "mCurrentFocus" in line]
        return " ".join(lines)

    def require_foreground(self) -> None:
        focus = self.current_focus()
        if self.package_name not in focus:
            raise AppStateError(
                f"Expected {self.package_name} in foreground, current focus: {focus}"
            )

    def launch(self) -> None:
        self.adb.run(
            "shell",
            "monkey",
            "-p",
            self.package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
            timeout=30,
        )
        time.sleep(1)
        self.require_foreground()

    def dump_tree(self, remote_path: str = "/sdcard/summer_ui.xml") -> UiTree:
        self.require_foreground()
        self.adb.run(
            "shell",
            "uiautomator",
            "dump",
            "--compressed",
            remote_path,
            timeout=30,
        )
        xml_text = self.adb.run("exec-out", "cat", remote_path, timeout=30, strip=False)
        return UiTree.from_xml(xml_text)

    def tap(
        self,
        x: int | UiNode,
        y: int | None = None,
        *,
        description: str = "tap",
        mutating: bool = False,
    ) -> bool:
        if isinstance(x, UiNode):
            point = x.center
        else:
            if y is None:
                raise ValueError("y is required when x is not a UiNode")
            point = (x, y)
        if mutating and not self.execute:
            self.audit.record("dry_run_tap", description=description, x=point[0], y=point[1])
            return False
        self.audit.record("tap", description=description, x=point[0], y=point[1], mutating=mutating)
        self.adb.run("shell", "input", "tap", str(point[0]), str(point[1]))
        time.sleep(0.4)
        return True

    def swipe(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        *,
        duration_ms: int = 500,
        description: str = "swipe",
    ) -> None:
        self.audit.record("swipe", description=description, start=start, end=end)
        self.adb.run(
            "shell",
            "input",
            "swipe",
            str(start[0]),
            str(start[1]),
            str(end[0]),
            str(end[1]),
            str(duration_ms),
        )
        time.sleep(0.7)

    def back(self, times: int = 1) -> None:
        for _ in range(times):
            self.adb.run("shell", "input", "keyevent", "BACK")
            time.sleep(0.5)

    def wait_for(
        self,
        predicate,
        *,
        timeout: float = 8,
        interval: float = 0.5,
        description: str = "condition",
    ):
        deadline = time.monotonic() + timeout
        last_value = None
        while time.monotonic() < deadline:
            last_value = predicate()
            if last_value:
                return last_value
            time.sleep(interval)
        raise AppStateError(f"Timed out waiting for {description}")

    def get_default_ime(self) -> str:
        return self.adb.run("shell", "settings", "get", "secure", "default_input_method")

    def set_ime(self, ime: str) -> None:
        self.adb.run("shell", "ime", "set", ime)
        time.sleep(0.3)

    @contextmanager
    def adb_keyboard(self):
        previous = self.get_default_ime()
        self._previous_ime = previous
        if previous != ADB_KEYBOARD_IME:
            self.set_ime(ADB_KEYBOARD_IME)
        try:
            yield
        finally:
            if previous and previous != self.get_default_ime():
                self.set_ime(previous)

    def input_text(self, text: str, *, clear: bool = True, mutating: bool = True) -> bool:
        if mutating and not self.execute:
            self.audit.record("dry_run_input_text", text=text)
            return False
        if clear:
            self.adb.run("shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT")
            time.sleep(0.2)
        payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
        self.audit.record("input_text", text=text)
        self.adb.run(
            "shell",
            "am",
            "broadcast",
            "-a",
            "ADB_INPUT_B64",
            "--es",
            "msg",
            payload,
        )
        time.sleep(0.7)
        return True

    def require_node(self, tree: UiTree, resource_id: str) -> UiNode:
        node = tree.find_by_id(resource_id)
        if node is None:
            raise UiElementNotFound(resource_id)
        return node

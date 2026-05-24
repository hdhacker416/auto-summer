from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import SafetyError


@dataclass
class SafetyConfig:
    execute: bool = False
    max_batch: int = 5
    package_name: str = "cn.imsummer.summer"
    audit_log: Path | None = None
    log_message_content: bool = False

    def require_execute(self, action: str) -> None:
        if not self.execute:
            raise SafetyError(
                f"Dry-run blocked mutating action: {action}. "
                "Use execute=True or --execute to run it."
            )

    def check_batch(self, requested: int) -> None:
        if requested > self.max_batch:
            raise SafetyError(
                f"Requested batch size {requested} exceeds max_batch={self.max_batch}."
            )


class AuditLogger:
    def __init__(self, path: Path | None, *, log_message_content: bool = False):
        self.path = path
        self.log_message_content = log_message_content

    def record(self, event: str, **data: Any) -> None:
        if not self.path:
            return
        safe_data = dict(data)
        if not self.log_message_content:
            for key in ("text", "message", "history", "answers"):
                if key in safe_data:
                    safe_data[key] = "<redacted>"
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **safe_data,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

"""Append-only, thread-safe JSONL event storage."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


class EventLog:
    """Persist one durable JSON object per line without rewriting prior attempts."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> None:
        encoded = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        with self._lock, self.path.open("ab") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())


def read_events(path: Path) -> list[dict[str, Any]]:
    """Load a complete event log, rejecting partial or non-object records."""
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"could not read event log {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number} of {path}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"event on line {line_number} of {path} is not an object")
        events.append(event)
    return events

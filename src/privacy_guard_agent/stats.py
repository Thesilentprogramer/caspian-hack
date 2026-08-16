from __future__ import annotations

import threading
import time
from typing import Any

from privacy_guard.types import Category


class Stats:
    """Process-local redaction counters for the Channel Adapter. Never stores values."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = time.monotonic()
        self.skipped = 0
        self.acked = 0
        self.completed = 0
        self.by_category: dict[str, int] = {category.value: 0 for category in Category}
        self.model = ""
        self.channels: dict[str, bool] = {"slack": False, "email": False, "telegram": False}

    def configure(self, *, model: str, channels: dict[str, bool]) -> None:
        with self._lock:
            self.model = model
            self.channels = dict(channels)

    def record_skip(self) -> None:
        with self._lock:
            self.skipped += 1

    def record_ack(self) -> None:
        with self._lock:
            self.acked += 1

    def record_complete(self, report: dict[str, int]) -> None:
        with self._lock:
            self.completed += 1
            for category, count in report.items():
                self.by_category[category] = self.by_category.get(category, 0) + count

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            by_category = dict(self.by_category)
            kept = sum(by_category.values())
            return {
                "kept_off_featherless": kept,
                "completed": self.completed,
                "skipped": self.skipped,
                "acked": self.acked,
                "by_category": by_category,
                "uptime_seconds": int(time.monotonic() - self._started),
                "model": self.model,
                "channels": dict(self.channels),
                "waiting": self.completed == 0 and self.skipped == 0 and self.acked == 0,
            }

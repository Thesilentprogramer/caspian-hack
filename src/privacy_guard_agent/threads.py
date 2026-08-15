from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

Clock = Callable[[], float]

THREAD_TTL_SECONDS = 30 * 60
MAX_TURNS = 12


@dataclass
class ThreadRoster:
    """In-process Slack/Email thread stickiness + sanitized history. Gone on restart."""

    ttl_seconds: float = THREAD_TTL_SECONDS
    max_turns: int = MAX_TURNS
    clock: Clock | None = None
    _clock: Clock = field(init=False, repr=False)
    _last: dict[str, float] = field(default_factory=dict)
    _history: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    _mapping: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._clock = self.clock or time.monotonic

    def is_warm(self, conversation_id: str | None) -> bool:
        self._expire()
        if not conversation_id:
            return False
        return conversation_id in self._last

    def touch(self, conversation_id: str | None) -> None:
        if not conversation_id:
            return
        self._last[conversation_id] = self._clock()

    def mapping_id(self, conversation_id: str | None) -> str | None:
        self._expire()
        if not conversation_id:
            return None
        return self._mapping.get(conversation_id)

    def set_mapping_id(self, conversation_id: str | None, mapping_id: str) -> None:
        if not conversation_id:
            return
        self._mapping[conversation_id] = mapping_id

    def history(self, conversation_id: str | None) -> list[dict[str, str]]:
        self._expire()
        if not conversation_id:
            return []
        return list(self._history.get(conversation_id, []))

    def append(self, conversation_id: str | None, role: str, content: str) -> None:
        if not conversation_id:
            return
        turns = self._history.setdefault(conversation_id, [])
        turns.append({"role": role, "content": content})
        overflow = len(turns) - self.max_turns
        if overflow > 0:
            del turns[:overflow]

    def drop(self, conversation_id: str) -> None:
        self._last.pop(conversation_id, None)
        self._history.pop(conversation_id, None)
        self._mapping.pop(conversation_id, None)

    def _expire(self) -> None:
        now = self._clock()
        dead = [cid for cid, seen in self._last.items() if now - seen >= self.ttl_seconds]
        for cid in dead:
            self.drop(cid)

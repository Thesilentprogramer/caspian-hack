from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from privacy_guard.guard import Guard


@pytest.fixture
def guard() -> Guard:
    return Guard(use_ner=False)


@dataclass
class FakeMessage:
    text: str
    replies: list[str] = field(default_factory=list)
    typed: bool = False
    streamed: bool = False

    def reply(self, text: str) -> None:
        self.replies.append(text)

    def typing(self) -> None:
        self.typed = True

    def stream(self):  # pragma: no cover - must never be called
        self.streamed = True
        raise AssertionError("Channel Adapter must not stream; Restore needs the full reply")

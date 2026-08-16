from __future__ import annotations

import pytest

from privacy_guard.guard import Guard


@pytest.fixture(autouse=True)
def _clear_category_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRIVACY_GUARD_CATEGORIES", raising=False)


@pytest.fixture
def guard() -> Guard:
    return Guard(use_ner=False)

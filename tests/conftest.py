from __future__ import annotations

import pytest

from privacy_guard.guard import Guard


@pytest.fixture
def guard() -> Guard:
    return Guard(use_ner=False)

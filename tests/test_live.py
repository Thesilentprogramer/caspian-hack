from __future__ import annotations

import os

import pytest

from privacy_guard.guard import Guard
from privacy_guard_agent.llm import FeatherlessCompleter


@pytest.mark.live
def test_featherless_sees_placeholders_not_raw_values() -> None:
    if not os.environ.get("FEATHERLESS_API_KEY"):
        pytest.skip("FEATHERLESS_API_KEY not set")
    guard = Guard(use_ner=False)
    original = "connect to 192.168.1.105 with sk_live_abc123"
    result = guard.sanitize(original)
    assert "192.168.1.105" not in result.safe_text
    assert "sk_live_abc123" not in result.safe_text
    reply = FeatherlessCompleter.from_env().complete(result.safe_text)
    restored = guard.restore(reply, result.mapping_id)
    assert isinstance(restored, str)

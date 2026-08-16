from __future__ import annotations

import pytest

from privacy_guard.guard import Guard
from privacy_guard.types import Category, categories_from_env
from privacy_guard_agent.handler import handle_message
from privacy_guard_agent.llm import FakeCompleter
from privacy_guard_agent.triage import Decision, triage
from test_agent_handler import FakeMessage


def test_unset_allowlist_is_all_seven() -> None:
    assert categories_from_env() == frozenset(Category)


def test_empty_allowlist_redacts_nothing() -> None:
    assert categories_from_env("") == frozenset()
    assert categories_from_env("   ") == frozenset()
    guard = Guard(use_ner=False, categories=frozenset())
    text = "host 192.168.1.105 key sk_live_abc123"
    result = guard.sanitize(text)
    assert result.safe_text == text


def test_unknown_category_fails() -> None:
    with pytest.raises(ValueError, match="unknown"):
        categories_from_env("EMAIL,NOT_A_THING")


def test_allowlist_keeps_api_key_passes_ip() -> None:
    guard = Guard(use_ner=False, categories=frozenset({Category.API_KEY}))
    text = "host 192.168.1.105 key sk_live_abc123"
    result = guard.sanitize(text)
    assert "192.168.1.105" in result.safe_text
    assert "sk_live_abc123" not in result.safe_text
    assert "[API_KEY_" in result.safe_text


def test_env_allowlist_used_when_categories_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRIVACY_GUARD_CATEGORIES", "EMAIL")
    guard = Guard(use_ner=False)
    result = guard.sanitize("ada@example.com at 10.0.0.1")
    assert "ada@example.com" not in result.safe_text
    assert "10.0.0.1" in result.safe_text


def test_channel_ip_skips_when_ip_not_allowed() -> None:
    allowed = frozenset({Category.API_KEY})
    message = FakeMessage("the router is 192.168.1.105", chat_type="channel")
    assert triage(message, categories=allowed) is Decision.SKIP
    completer = FakeCompleter()
    handle_message(message, Guard(use_ner=False, categories=allowed), completer)
    assert completer.seen == []
    assert message.replies == []


def test_telegram_is_directed() -> None:
    message = FakeMessage("what is the status", channel="telegram", chat_type="group")
    assert triage(message) is Decision.COMPLETE

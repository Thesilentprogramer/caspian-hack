from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from privacy_guard.guard import Guard
from privacy_guard.types import MappingExpired

EMAIL = st.from_regex(r"[a-z]{3,8}@[a-z]{3,8}\.com", fullmatch=True)
IPV4 = st.from_regex(
    r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)",
    fullmatch=True,
)


def test_regex_round_trip_demo_sentence(guard: Guard) -> None:
    text = (
        "having trouble connecting to 192.168.1.105 with key sk_live_abc123, "
        "can you help Rohan out?"
    )
    result = guard.sanitize(text)
    assert "192.168.1.105" not in result.safe_text
    assert "sk_live_abc123" not in result.safe_text
    assert "[IP_ADDRESS_" in result.safe_text
    assert "[API_KEY_" in result.safe_text
    restored = guard.restore(result.safe_text, result.mapping_id)
    assert restored == text


def test_same_value_same_placeholder(guard: Guard) -> None:
    text = "mail ada@example.com and also ada@example.com again"
    result = guard.sanitize(text)
    assert result.safe_text.count("[EMAIL_") == 2
    first, _, rest = result.safe_text.partition("[EMAIL_")
    token = "[EMAIL_" + rest.split("]", 1)[0] + "]"
    assert result.safe_text.count(token) == 2
    assert guard.restore(result.safe_text, result.mapping_id) == text


def test_plain_text_passthrough(guard: Guard) -> None:
    text = "nothing sensitive here"
    result = guard.sanitize(text)
    assert result.safe_text == text
    assert guard.restore(result.safe_text, result.mapping_id) == text


def test_unknown_mapping_raises(guard: Guard) -> None:
    with pytest.raises(MappingExpired):
        guard.restore("hello", "not-a-real-id")


def test_expired_mapping_raises() -> None:
    clock = {"now": 0.0}
    from privacy_guard._mapping import MappingStore

    guard = Guard(store=MappingStore(ttl_seconds=5, clock=lambda: clock["now"]), use_ner=False)
    result = guard.sanitize("ada@example.com")
    clock["now"] = 10.0
    with pytest.raises(MappingExpired):
        guard.restore(result.safe_text, result.mapping_id)


def test_restore_in_llm_shaped_reply(guard: Guard) -> None:
    original = "whitelist 10.0.0.1 please"
    result = guard.sanitize(original)
    llm = f"Sure — please whitelist {result.safe_text.split()[-2]} on the firewall."
    restored = guard.restore(llm, result.mapping_id)
    assert "10.0.0.1" in restored
    assert "[IP_ADDRESS_" not in restored


@given(EMAIL)
@settings(max_examples=40, deadline=None)
def test_email_round_trip_property(email: str) -> None:
    guard = Guard(use_ner=False)
    text = f"contact {email} tomorrow"
    result = guard.sanitize(text)
    assert email not in result.safe_text
    assert guard.restore(result.safe_text, result.mapping_id) == text


@given(IPV4)
@settings(max_examples=40, deadline=None)
def test_ip_round_trip_property(ip: str) -> None:
    guard = Guard(use_ner=False)
    text = f"host {ip} is down"
    result = guard.sanitize(text)
    assert ip not in result.safe_text
    assert guard.restore(result.safe_text, result.mapping_id) == text


def test_module_level_sanitize_restore_share_default_guard() -> None:
    from privacy_guard import restore, sanitize

    result = sanitize("mail zed@example.com")
    assert "zed@example.com" not in result.safe_text
    assert restore(result.safe_text, result.mapping_id).endswith("zed@example.com")

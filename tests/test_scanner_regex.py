from __future__ import annotations

import json
from pathlib import Path

import pytest

from privacy_guard._scanner import RegexScanner, luhn_ok, resolve_overlaps
from privacy_guard.types import Category, Span

FIXTURES = Path(__file__).parent / "fixtures" / "messages.json"


def test_luhn_accepts_visa_test_pan() -> None:
    assert luhn_ok("4111111111111111")


def test_luhn_rejects_invalid_pan() -> None:
    assert not luhn_ok("4111111111111112")


def test_golden_fixtures() -> None:
    scanner = RegexScanner()
    cases = json.loads(FIXTURES.read_text())
    for case in cases:
        found = {(s.category.value, s.value) for s in scanner.scan(case["text"])}
        expected = {(item["category"], item["value"]) for item in case["expect"]}
        assert expected <= found, case["name"]


def test_invalid_card_is_not_redacted() -> None:
    scanner = RegexScanner()
    text = "card 4111111111111112 is bad"
    cats = {s.category for s in scanner.scan(text)}
    assert Category.CREDIT_CARD not in cats


def test_overlap_api_key_beats_phone_shaped_digits() -> None:
    # A long digit run that is a valid card should win over a phone nested in it.
    card = Span(0, 19, "4111 1111 1111 1111", Category.CREDIT_CARD)
    phone = Span(5, 17, "1111 1111 11", Category.PHONE)
    kept = resolve_overlaps([card, phone])
    assert kept == [card]


def test_longer_span_wins_same_priority() -> None:
    a = Span(0, 5, "short", Category.PERSON)
    b = Span(0, 11, "short longer", Category.PERSON)
    kept = resolve_overlaps([a, b])
    assert kept == [b]


def test_demo_sentence_catches_ip_and_key() -> None:
    scanner = RegexScanner()
    text = (
        "having trouble connecting to 192.168.1.105 with key sk_live_abc123, "
        "can you help Rohan out?"
    )
    found = {s.category: s.value for s in scanner.scan(text)}
    assert found[Category.IP_ADDRESS] == "192.168.1.105"
    assert found[Category.API_KEY] == "sk_live_abc123"


@pytest.mark.ner
def test_ner_catches_rohan() -> None:
    from privacy_guard._scanner import NerScanner

    if not NerScanner.available():
        pytest.skip("en_core_web_sm is not installed")
    spans = NerScanner().scan("can you help Rohan out?")
    names = {s.value for s in spans if s.category == Category.PERSON}
    assert any("Rohan" in name for name in names)


@pytest.mark.ner
def test_ner_documented_miss() -> None:
    from privacy_guard._scanner import NerScanner

    if not NerScanner.available():
        pytest.skip("en_core_web_sm is not installed")
        # Initials of a teammate are a known NER miss — the demo caveat, not a bug.
        spans = NerScanner().scan("talk to sj tomorrow")
        people = [s for s in spans if s.category == Category.PERSON]
        assert "sj" not in {s.value for s in people}
        assert people == []

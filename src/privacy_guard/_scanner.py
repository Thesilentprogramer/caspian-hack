from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from privacy_guard.types import CATEGORY_PRIORITY, Category, Span

_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
)
_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
)
_API_KEY = re.compile(
    r"\b(?:sk_live|sk_test|pk_live|pk_test)_[A-Za-z0-9]{6,}\b"
    r"|\bghp_[A-Za-z0-9]{20,}\b"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}\b",
)
# 13–19 digits, optional spaces or dashes between groups.
_CARD = re.compile(r"\b(?:\d[ \-]?){12,18}\d\b")
_PHONE = re.compile(
    r"(?<!\w)(?:\+?1[\s.\-]?)?(?:\(?\d{3}\)?[\s.\-]?)\d{3}[\s.\-]?\d{4}(?!\w)",
)

_NER_LABELS = {"PERSON": Category.PERSON, "ORG": Category.ORG, "GPE": Category.ORG}


def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def resolve_overlaps(spans: Sequence[Span]) -> list[Span]:
    """Keep the higher-priority (then longer) span when two overlap."""
    ranked = sorted(
        spans,
        key=lambda s: (
            -CATEGORY_PRIORITY[s.category],
            -(s.end - s.start),
            s.start,
        ),
    )
    kept: list[Span] = []
    for span in ranked:
        if any(span.overlaps(existing) for existing in kept):
            continue
        kept.append(span)
    kept.sort(key=lambda s: s.start)
    return kept


class RegexScanner:
    def scan(self, text: str) -> list[Span]:
        found: list[Span] = []
        found.extend(_spans(text, _EMAIL, Category.EMAIL))
        found.extend(_spans(text, _IPV4, Category.IP_ADDRESS))
        found.extend(_spans(text, _API_KEY, Category.API_KEY))
        found.extend(_card_spans(text))
        found.extend(_spans(text, _PHONE, Category.PHONE))
        return found


@dataclass
class NerScanner:
    """Best-effort Person/Org names. Missing model → empty scan, never a crash."""

    _nlp: object | None = None

    @classmethod
    def available(cls) -> bool:
        try:
            import spacy  # noqa: F401

            spacy.load("en_core_web_sm")
        except (OSError, ImportError):
            return False
        return True

    def _model(self):
        if self._nlp is None:
            import spacy

            self._nlp = spacy.load(
                "en_core_web_sm",
                disable=["parser", "lemmatizer", "attribute_ruler", "tagger"],
            )
        return self._nlp

    def scan(self, text: str) -> list[Span]:
        try:
            nlp = self._model()
        except (OSError, ImportError):
            return []
        doc = nlp(text)
        spans: list[Span] = []
        for ent in doc.ents:
            category = _NER_LABELS.get(ent.label_)
            if category is None:
                continue
            value = ent.text.strip()
            if not value:
                continue
            spans.append(Span(start=ent.start_char, end=ent.end_char, value=value, category=category))
        return spans


def scan_all(text: str, scanners: Sequence[object]) -> list[Span]:
    found: list[Span] = []
    for scanner in scanners:
        found.extend(scanner.scan(text))
    return resolve_overlaps(found)


def _spans(text: str, pattern: re.Pattern[str], category: Category) -> list[Span]:
    return [
        Span(start=m.start(), end=m.end(), value=m.group(0), category=category)
        for m in pattern.finditer(text)
    ]


def _card_spans(text: str) -> list[Span]:
    spans: list[Span] = []
    for match in _CARD.finditer(text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if luhn_ok(digits):
            spans.append(
                Span(start=match.start(), end=match.end(), value=raw, category=Category.CREDIT_CARD)
            )
    return spans

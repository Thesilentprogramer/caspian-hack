from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from privacy_guard._mapping import MappingStore
from privacy_guard._scanner import NerScanner, RegexScanner, scan_all
from privacy_guard.types import Category, MappingExpired, SanitizeResult, Span


def _placeholder_for(category: Category, value: str) -> str:
    digest = hashlib.sha256(f"{category}:{value}".encode()).hexdigest()[:8].upper()
    return f"[{category}_{digest}]"


@dataclass
class Guard:
    """Deep Privacy Guard module. Public interface: sanitize / restore."""

    store: MappingStore = field(default_factory=MappingStore)
    use_ner: bool | None = None
    _scanners: list[object] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        scanners: list[object] = [RegexScanner()]
        ner = self.use_ner
        if ner is None:
            ner = NerScanner.available()
        if ner:
            scanners.append(NerScanner())
        self._scanners = scanners

    def sanitize(self, text: str) -> SanitizeResult:
        mapping_id = self.store.create()
        spans = scan_all(text, self._scanners)
        if not spans:
            return SanitizeResult(safe_text=text, mapping_id=mapping_id)

        assigned: dict[tuple[Category, str], str] = {}
        for span in spans:
            key = (span.category, span.value)
            if key not in assigned:
                placeholder = _placeholder_for(span.category, span.value)
                assigned[key] = placeholder
                self.store.put(mapping_id, placeholder, span.value)

        safe = _replace_from_end(text, spans, assigned)
        return SanitizeResult(safe_text=safe, mapping_id=mapping_id)

    def restore(self, text: str, mapping_id: str) -> str:
        values = self.store.get_all(mapping_id)
        restored = text
        for placeholder, plaintext in sorted(values.items(), key=lambda kv: -len(kv[0])):
            restored = restored.replace(placeholder, plaintext)
        return restored


_default: Guard | None = None


def get_guard() -> Guard:
    global _default
    if _default is None:
        _default = Guard()
    return _default


def sanitize(text: str) -> SanitizeResult:
    return get_guard().sanitize(text)


def restore(text: str, mapping_id: str) -> str:
    return get_guard().restore(text, mapping_id)


def _replace_from_end(
    text: str,
    spans: list[Span],
    assigned: dict[tuple[Category, str], str],
) -> str:
    pieces: list[str] = []
    cursor = len(text)
    for span in sorted(spans, key=lambda s: s.start, reverse=True):
        pieces.append(text[span.end : cursor])
        pieces.append(assigned[(span.category, span.value)])
        cursor = span.start
    pieces.append(text[:cursor])
    pieces.reverse()
    return "".join(pieces)


__all__ = ["Guard", "MappingExpired", "sanitize", "restore", "get_guard"]

from __future__ import annotations

import re

_PLACEHOLDER = re.compile(r"\[[A-Z][A-Z0-9_]{2,}\]")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_UNDER = re.compile(r"__(.+?)__")
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_STAR_BULLET = re.compile(r"^[ \t]*\*[ \t]+", re.MULTILINE)
_DASH_BULLET = re.compile(r"^[ \t]*-[ \t]+", re.MULTILINE)


def to_plain(text: str) -> str:
    """Strip Markdown markers. Placeholders like [IP_ADDRESS_F5BA] stay intact."""
    holders: dict[str, str] = {}

    def _stash(match: re.Match[str]) -> str:
        token = f"\x00PH{len(holders)}\x00"
        holders[token] = match.group(0)
        return token

    protected = _PLACEHOLDER.sub(_stash, text)
    protected = _BOLD.sub(r"\1", protected)
    protected = _UNDER.sub(r"\1", protected)
    protected = _HEADING.sub("", protected)
    protected = _STAR_BULLET.sub("• ", protected)
    protected = _DASH_BULLET.sub("• ", protected)
    for token, original in holders.items():
        protected = protected.replace(token, original)
    return protected.strip()

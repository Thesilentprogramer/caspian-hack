from __future__ import annotations

from privacy_guard.guard import Guard
from privacy_guard.types import SanitizeResult


class SessionGuard:
    """One Mapping Id for the MCP process so placeholders stay stable."""

    def __init__(self, guard: Guard) -> None:
        self.guard = guard
        self.mapping_id: str | None = None

    def sanitize(self, text: str) -> SanitizeResult:
        result = self.guard.sanitize(text, mapping_id=self.mapping_id)
        self.mapping_id = result.mapping_id
        return result

    def restore(self, text: str, mapping_id: str) -> str:
        return self.guard.restore(text, mapping_id)

    def redaction_report(self, mapping_id: str | None = None) -> dict[str, int]:
        mid = mapping_id or self.mapping_id
        if not mid:
            return {}
        return self.guard.redaction_report(mid)

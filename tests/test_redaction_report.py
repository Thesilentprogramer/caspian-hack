from __future__ import annotations

import pytest

from privacy_guard.guard import Guard
from privacy_guard.types import MappingExpired
from privacy_guard_mcp.server import redaction_report, sanitize


def test_report_counts_unique_placeholders_not_values(guard: Guard) -> None:
    text = "mail ada@example.com and also ada@example.com then 10.0.0.1"
    result = guard.sanitize(text)
    report = guard.redaction_report(result.mapping_id)
    assert report == {"EMAIL": 1, "IP_ADDRESS": 1}
    blob = str(report)
    assert "ada@example.com" not in blob
    assert "10.0.0.1" not in blob


def test_report_expired_mapping_raises(guard: Guard) -> None:
    with pytest.raises(MappingExpired):
        guard.redaction_report("missing-id")


def test_mcp_report_tool_hides_values() -> None:
    payload = sanitize("box 192.168.1.105 key sk_live_abc123")
    report = redaction_report(payload["mapping_id"])
    assert report.get("IP_ADDRESS") == 1
    assert report.get("API_KEY") == 1
    assert "error" not in report
    assert "192.168.1.105" not in str(report)
    assert "sk_live_abc123" not in str(report)


def test_mcp_report_expired_mapping() -> None:
    out = redaction_report("missing-id")
    assert out.get("error", "").startswith("mapping expired")
    assert "EMAIL" not in out

from __future__ import annotations

import pytest

from privacy_guard_mcp.server import mcp, restore, sanitize


@pytest.mark.asyncio
async def test_sanitize_restore_tools_in_memory() -> None:
    text = "box 192.168.1.105 key sk_live_abc123"
    try:
        from mcp import Client
    except ImportError:
        Client = None  # type: ignore[misc, assignment]

    if Client is not None:
        try:
            async with Client(mcp) as client:  # type: ignore[arg-type]
                sanitized = await client.call_tool("sanitize", {"text": text})
                payload = _structured(sanitized)
                assert "192.168.1.105" not in payload["safe_text"]
                restored = await client.call_tool(
                    "restore",
                    {"text": payload["safe_text"], "mapping_id": payload["mapping_id"]},
                )
                assert _structured(restored)["restored_text"] == text
                return
        except (TypeError, AttributeError):
            pass

    try:
        from mcp.shared.memory import create_connected_server_and_client_session as create_session
    except ImportError:
        create_session = None

    if create_session is not None:
        async with create_session(mcp._mcp_server) as session:
            await session.initialize()
            sanitized = await session.call_tool("sanitize", {"text": text})
            payload = _tool_text_json(sanitized)
            assert "192.168.1.105" not in payload["safe_text"]
            restored = await session.call_tool(
                "restore",
                {"text": payload["safe_text"], "mapping_id": payload["mapping_id"]},
            )
            assert _tool_text_json(restored)["restored_text"] == text
            return

    # Last resort: call the registered functions (still covers the Guard seam).
    payload = sanitize(text)
    assert "sk_live_abc123" not in payload["safe_text"]
    assert restore(payload["safe_text"], payload["mapping_id"])["restored_text"] == text


def test_tools_round_trip_direct() -> None:
    text = "mail ada@example.com"
    payload = sanitize(text)
    assert "ada@example.com" not in payload["safe_text"]
    out = restore(payload["safe_text"], payload["mapping_id"])
    assert out["restored_text"] == text


def test_restore_expired_mapping_reports_error() -> None:
    out = restore("hello", "missing-id")
    assert out["restored_text"] == ""
    assert "expired" in out["error"]


def _structured(result: object) -> dict[str, str]:
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    return _tool_text_json(result)


def _tool_text_json(result: object) -> dict[str, str]:
    import json

    content = getattr(result, "content", None)
    if content:
        text = getattr(content[0], "text", None)
        if text:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
    raise AssertionError(f"could not parse tool result: {result!r}")

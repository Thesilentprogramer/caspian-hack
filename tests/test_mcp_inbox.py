from __future__ import annotations

from privacy_guard.guard import Guard
from privacy_guard_mcp.http import BearerAuthMiddleware, require_http_token, run_http
from privacy_guard_mcp.inbox import Inbox
from privacy_guard_mcp.server import mcp
from privacy_guard_mcp.session import SessionGuard

SECRET_IP = "192.168.1.105"
SECRET_KEY = "sk_live_abc123"
BODY = f"having trouble connecting to {SECRET_IP} with key {SECRET_KEY}"


class FakeCaspian:
    def __init__(self) -> None:
        self.backfill_calls: list[tuple[str, int]] = []

    def list_connections(self, channel: str | None = None) -> list[dict]:
        return [
            {"id": "conn_slack", "channel": "slack"},
            {"id": "conn_email", "channel": "email"},
        ]

    def list_conversations(self, connection_id: str | None = None) -> list[dict]:
        rows = [
            {
                "id": "conv_old",
                "connection_id": "conn_email",
                "created_at": "2026-01-01T00:00:00",
            },
            {
                "id": "conv_new",
                "connection_id": "conn_slack",
                "created_at": "2026-08-16T12:00:00",
            },
        ]
        if connection_id:
            return [row for row in rows if row["connection_id"] == connection_id]
        return rows

    def list_messages(self, conversation_id: str) -> list[dict]:
        if conversation_id == "conv_new":
            return [
                {
                    "channel": "slack",
                    "direction": "inbound",
                    "created_at": "2026-08-16T12:01:00",
                    "text": BODY,
                }
            ]
        return [
            {
                "channel": "email",
                "direction": "inbound",
                "created_at": "2026-01-01T00:01:00",
                "text": "hello from email",
            }
        ]

    def backfill(self, conversation_id: str, limit: int = 50) -> dict:
        self.backfill_calls.append((conversation_id, limit))
        return {"ok": True}


def _inbox() -> Inbox:
    return Inbox(FakeCaspian(), SessionGuard(Guard(use_ner=False)))


def test_list_inbox_sanitizes_preview() -> None:
    payload = _inbox().list_inbox()
    assert payload["conversations"][0]["conversation_id"] == "conv_new"
    preview = payload["conversations"][0]["preview"]
    assert SECRET_IP not in preview
    assert SECRET_KEY not in preview
    assert "IP_ADDRESS" in preview
    assert "API_KEY" in preview
    report = payload["redaction_report"]
    assert report.get("IP_ADDRESS") == 1
    assert report.get("API_KEY") == 1
    assert payload["mapping_id"]


def test_get_thread_and_brief_status_never_leak_secrets() -> None:
    box = _inbox()
    thread = box.get_thread("conv_new")
    assert SECRET_IP not in thread["safe_text"]
    assert SECRET_KEY not in thread["safe_text"]
    brief = box.brief_status(n=2, m=10)
    assert SECRET_IP not in brief["safe_text"]
    assert SECRET_KEY not in brief["safe_text"]
    assert "conv_new" in brief["safe_text"]
    assert thread["mapping_id"] == brief["mapping_id"]


def test_get_thread_backfill_calls_caspian() -> None:
    fake = FakeCaspian()
    box = Inbox(fake, SessionGuard(Guard(use_ner=False)))
    box.get_thread("conv_new", backfill=True, limit=10)
    assert fake.backfill_calls == [("conv_new", 10)]


def test_list_inbox_via_mock_http() -> None:
    import httpx
    from caspian_sdk import CommClient

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/connections"):
            return httpx.Response(200, json=[{"id": "conn_slack", "channel": "slack"}])
        if path.endswith("/conversations"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "conv_new",
                        "connection_id": "conn_slack",
                        "created_at": "2026-08-16T12:00:00",
                    }
                ],
            )
        if path.endswith("/messages"):
            return httpx.Response(
                200,
                json=[
                    {
                        "channel": "slack",
                        "direction": "inbound",
                        "created_at": "2026-08-16T12:01:00",
                        "text": BODY,
                    }
                ],
            )
        return httpx.Response(404, json={"detail": path})

    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://gw.test")
    client = CommClient(api_key="comm_test_key", base_url="http://gw.test", http=http)
    try:
        payload = Inbox(client, SessionGuard(Guard(use_ner=False))).list_inbox()
    finally:
        client.close()
    preview = payload["conversations"][0]["preview"]
    assert SECRET_IP not in preview
    assert SECRET_KEY not in preview


def test_inbox_tools_registered() -> None:
    names = {tool.name for tool in mcp._tool_manager.list_tools()}
    assert names >= {
        "sanitize",
        "restore",
        "redaction_report",
        "list_inbox",
        "get_thread",
        "brief_status",
    }


def test_http_rejects_non_loopback() -> None:
    try:
        run_http(object(), host="0.0.0.0")
    except ValueError as exc:
        assert "loopback" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_http_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    try:
        require_http_token()
    except SystemExit as exc:
        assert "MCP_AUTH_TOKEN" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_bearer_middleware_rejects_bad_token() -> None:
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def ping(_request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/ping", ping)])
    app.add_middleware(BearerAuthMiddleware, expected="secret-token")
    client = TestClient(app)
    denied = client.get("/ping")
    assert denied.status_code == 401
    allowed = client.get("/ping", headers={"Authorization": "Bearer secret-token"})
    assert allowed.status_code == 200
    assert allowed.text == "ok"

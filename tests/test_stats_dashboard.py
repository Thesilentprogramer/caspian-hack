from __future__ import annotations

import json
from urllib.request import urlopen

from privacy_guard.guard import Guard
from privacy_guard_agent.dashboard import start_dashboard
from privacy_guard_agent.handler import handle_message, telegram_token
from privacy_guard_agent.llm import FakeCompleter
from privacy_guard_agent.stats import Stats
from test_agent_handler import FakeMessage


def test_telegram_token_blank_is_disabled(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram_token() == ""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "  ")
    assert telegram_token() == ""


def test_telegram_token_present_not_logged_by_helper(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:secret-bot-token")
    assert telegram_token() == "123:secret-bot-token"


def test_stats_increment_without_storing_values() -> None:
    stats = Stats()
    guard = Guard(use_ner=False)
    handle_message(
        FakeMessage("host 192.168.1.105 key sk_live_abc123"),
        guard,
        FakeCompleter(),
        stats=stats,
    )
    snap = stats.snapshot()
    blob = json.dumps(snap)
    assert "192.168.1.105" not in blob
    assert "sk_live_abc123" not in blob
    assert snap["completed"] == 1
    assert snap["kept_off_featherless"] == 2
    assert snap["by_category"]["IP_ADDRESS"] == 1
    assert snap["by_category"]["API_KEY"] == 1
    assert snap["waiting"] is False


def test_stats_records_skip() -> None:
    stats = Stats()
    handle_message(
        FakeMessage("the project is live now", chat_type="channel"),
        Guard(use_ner=False),
        FakeCompleter(),
        stats=stats,
    )
    assert stats.snapshot()["skipped"] == 1
    assert stats.snapshot()["completed"] == 0


def test_dashboard_stats_json_and_page() -> None:
    stats = Stats()
    stats.configure(model="test-model", channels={"slack": True, "email": True, "telegram": False})
    stats.record_complete({"EMAIL": 1})
    server = start_dashboard(stats, port=0)
    try:
        host, port = server.server_address
        with urlopen(f"http://{host}:{port}/stats.json", timeout=2) as response:
            payload = json.loads(response.read().decode())
        assert payload["kept_off_featherless"] == 1
        assert payload["model"] == "test-model"
        assert payload["channels"]["telegram"] is False
        with urlopen(f"http://{host}:{port}/", timeout=2) as response:
            page = response.read().decode()
        assert "kept off Featherless" in page
        assert "sk_live" not in page
    finally:
        server.shutdown()
        server.server_close()

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from privacy_guard.guard import Guard
from privacy_guard_agent.llm import FeatherlessCompleter

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

DEMO = (
    "having trouble connecting to 192.168.1.105 with key sk_live_abc123, "
    "can you help Rohan out?"
)
_SECRETS = ("192.168.1.105", "sk_live_abc123")
_PLACEHOLDER_MARKERS = ("[IP_ADDRESS_", "[API_KEY_")


def _caspian():
    if not os.environ.get("CASPIAN_API_KEY"):
        pytest.skip("CASPIAN_API_KEY not set")
    from caspian_sdk import CommClient

    return CommClient()


def _active_connection(client, channel: str) -> dict:
    found = [
        conn
        for conn in client.list_connections()
        if conn.get("channel") == channel and conn.get("status") == "active"
    ]
    assert found, f"no active {channel} connection — is privacy-guard-agent authorized?"
    return found[0]


def _message(event: dict) -> dict:
    data = event.get("data") or {}
    msg = data.get("message") or data
    return msg if isinstance(msg, dict) else {}


def _latest_seq(client) -> int:
    events = client.events(limit=1)
    return int(events[0]["seq"]) if events else 0


def _wait_for_message(
    client,
    *,
    event_type: str,
    after_seq: int,
    channel: str,
    conversation_id: str | None = None,
    text_contains: str | None = None,
    timeout: float = 120.0,
) -> dict:
    deadline = time.time() + timeout
    last_seq = after_seq
    while time.time() < deadline:
        for event in client.events(after_seq=last_seq, limit=100, type=event_type):
            last_seq = max(last_seq, int(event.get("seq") or last_seq))
            msg = _message(event)
            if (msg.get("channel") or "").lower() != channel:
                continue
            if conversation_id and msg.get("conversation_id") != conversation_id:
                continue
            text = msg.get("text") or ""
            if text_contains and text_contains not in text:
                continue
            return msg
        time.sleep(2)
    hint = " Is privacy-guard-agent listening?" if event_type == "message.sent" else ""
    pytest.fail(f"timed out waiting for {channel} {event_type} after seq {after_seq}.{hint}")


@pytest.mark.live
def test_featherless_sees_placeholders_not_raw_values() -> None:
    if not os.environ.get("FEATHERLESS_API_KEY"):
        pytest.skip("FEATHERLESS_API_KEY not set")
    guard = Guard(use_ner=False)
    result = guard.sanitize(DEMO)
    for secret in _SECRETS:
        assert secret not in result.safe_text
    reply = FeatherlessCompleter.from_env().complete(result.safe_text)
    for secret in _SECRETS:
        assert secret not in reply
    restored = guard.restore(reply, result.mapping_id)
    assert isinstance(restored, str)


@pytest.mark.live
def test_slack_connection_is_active() -> None:
    client = _caspian()
    slack = _active_connection(client, "slack")
    address = slack.get("address") or ""
    assert address.startswith("slack:"), address
    convos = client.list_conversations(connection_id=slack["id"])
    assert convos, "active Slack connection has no conversations"
    messages = client.list_messages(convos[0]["id"])
    assert messages, "Slack conversation has no messages — mention the bot in Slack"


@pytest.mark.live
def test_email_connection_is_active() -> None:
    client = _caspian()
    inbox = _active_connection(client, "email")
    assert inbox.get("address") == "privacy-guard@agents.trycaspianai.com"


@pytest.mark.live
def test_email_roundtrip_restores_secrets() -> None:
    client = _caspian()
    inbox = _active_connection(client, "email")
    marker = f"LIVE-EMAIL-{uuid.uuid4().hex[:8]}"
    after_seq = _latest_seq(client)
    client.test_email(
        text=f"{marker} {DEMO}",
        subject=f"Privacy Guard live check {marker}",
        connection_id=inbox["id"],
    )
    inbound = _wait_for_message(
        client,
        event_type="message.received",
        after_seq=after_seq,
        channel="email",
        text_contains=marker,
    )
    outbound = _wait_for_message(
        client,
        event_type="message.sent",
        after_seq=after_seq,
        channel="email",
        conversation_id=inbound.get("conversation_id"),
    )
    text = outbound.get("text") or ""
    for marker_text in _PLACEHOLDER_MARKERS:
        assert marker_text not in text
    for secret in _SECRETS:
        assert secret in text

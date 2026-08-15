from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from privacy_guard.guard import Guard
from privacy_guard_agent.handler import handle_message
from privacy_guard_agent.llm import SYSTEM_PROMPT, FakeCompleter, FeatherlessCompleter
from privacy_guard_agent.outbound import to_plain
from privacy_guard_agent.triage import Decision, triage


@dataclass
class FakeMessage:
    text: str
    channel: str = "slack"
    chat_type: str | None = "dm"
    sender: dict | None = None
    replies: list[str] = field(default_factory=list)
    reactions: list[str] = field(default_factory=list)
    typed: bool = False
    streamed: bool = False

    def reply(self, text: str) -> None:
        self.replies.append(text)

    def typing(self) -> None:
        self.typed = True

    def react(self, emoji: str) -> None:
        self.reactions.append(emoji)

    def stream(self):  # pragma: no cover
        self.streamed = True
        raise AssertionError("Channel Adapter must not stream; Restore needs the full reply")


def test_handler_sends_only_safe_text_to_completer() -> None:
    guard = Guard(use_ner=False)
    completer = FakeCompleter()
    message = FakeMessage("having trouble connecting to 192.168.1.105 with key sk_live_abc123")
    handle_message(message, guard, completer)

    assert completer.seen
    sent = completer.seen[0]
    assert "192.168.1.105" not in sent
    assert "sk_live_abc123" not in sent
    assert "[IP_ADDRESS_" in sent
    assert "[API_KEY_" in sent

    assert len(message.replies) == 1
    reply = message.replies[0]
    assert "192.168.1.105" in reply
    assert "sk_live_abc123" in reply
    assert "**" not in reply
    assert not message.streamed
    assert message.typed


def test_handler_never_calls_stream() -> None:
    class StreamingMessage(FakeMessage):
        def stream(self):
            self.streamed = True
            raise AssertionError("stream must not be used")

    handle_message(
        StreamingMessage("ada@example.com is down"),
        Guard(use_ner=False),
        FakeCompleter(),
    )


def test_handler_fallback_on_expired_mapping() -> None:
    guard = Guard(use_ner=False)
    completer = FakeCompleter()
    message = FakeMessage("host 10.0.0.1")

    original_complete = completer.complete

    def expire_then_complete(text: str, channel: str | None = None, etiquette: str = "") -> str:
        out = original_complete(text, channel=channel, etiquette=etiquette)
        for mid in list(guard.store._maps):
            guard.store.drop(mid)
        return out

    completer.complete = expire_then_complete  # type: ignore[method-assign]
    handle_message(message, guard, completer)
    assert message.replies
    assert "mapping expired" in message.replies[0].lower()
    assert "10.0.0.1" not in message.replies[0] or "resend" in message.replies[0].lower()


def test_empty_message_skips() -> None:
    completer = FakeCompleter()
    message = FakeMessage("   ")
    handle_message(message, Guard(use_ner=False), completer)
    assert message.replies == []
    assert completer.seen == []


def test_channel_chatter_does_not_call_completer() -> None:
    completer = FakeCompleter()
    message = FakeMessage("the project is live now", chat_type="channel")
    assert triage(message) is Decision.SKIP
    handle_message(message, Guard(use_ner=False), completer)
    assert completer.seen == []
    assert message.replies == []


def test_thanks_dm_does_not_call_completer() -> None:
    completer = FakeCompleter()
    message = FakeMessage("thanks", chat_type="dm")
    handle_message(message, Guard(use_ner=False), completer)
    assert completer.seen == []
    assert message.reactions == ["thumbsup"]
    assert message.replies == []


def test_channel_mention_with_secret_calls_completer() -> None:
    completer = FakeCompleter()
    message = FakeMessage(
        "<@U123> having trouble connecting to 192.168.1.105 with key sk_live_abc123",
        chat_type="channel",
    )
    handle_message(message, Guard(use_ner=False), completer)
    assert completer.seen
    assert "192.168.1.105" in message.replies[0]


def test_featherless_completer_uses_placeholders_in_request() -> None:
    captured: dict[str, object] = {}

    class FakeChoice:
        def __init__(self) -> None:
            self.message = type("M", (), {"content": "ok [IP_ADDRESS_AAAA]"})()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs: object) -> FakeResponse:
                    captured.update(kwargs)
                    return FakeResponse()

    completer = FeatherlessCompleter(api_key="test", client=FakeClient())  # type: ignore[arg-type]
    out = completer.complete("host [IP_ADDRESS_AAAA] is down", channel="slack")
    assert "[IP_ADDRESS_AAAA]" in out
    messages = captured["messages"]
    assert isinstance(messages, list)
    assert SYSTEM_PROMPT in messages[0]["content"]
    assert "Never use Markdown" in messages[0]["content"]
    assert "[IP_ADDRESS_AAAA]" in messages[1]["content"]
    assert captured["model"] == "Qwen/Qwen2.5-7B-Instruct"


def test_from_env_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FEATHERLESS_API_KEY"):
        FeatherlessCompleter.from_env()


def test_handler_replies_when_completer_fails() -> None:
    class Boom:
        def complete(self, text: str, channel: str | None = None, etiquette: str = "") -> str:
            raise RuntimeError("gated")

    message = FakeMessage("host 10.0.0.1")
    handle_message(message, Guard(use_ner=False), Boom())  # type: ignore[arg-type]
    assert message.replies
    assert "language model call failed" in message.replies[0].lower()
    assert "10.0.0.1" not in message.replies[0]


def test_handler_strips_markdown_asterisks() -> None:
    class MarkdownCompleter:
        def complete(self, text: str, channel: str | None = None, etiquette: str = "") -> str:
            return "**Subject:** please whitelist " + text

    message = FakeMessage("host 10.0.0.1")
    handle_message(message, Guard(use_ner=False), MarkdownCompleter())  # type: ignore[arg-type]
    assert message.replies
    assert "**" not in message.replies[0]
    assert "10.0.0.1" in message.replies[0]


def test_to_plain_strips_markdown_keeps_placeholder() -> None:
    raw = "**Subject:** whitelist [IP_ADDRESS_F5BA]\n* **API Routing:** fix it"
    out = to_plain(raw)
    assert out == "Subject: whitelist [IP_ADDRESS_F5BA]\n• API Routing: fix it"
    assert "**" not in out
    assert "[IP_ADDRESS_F5BA]" in out

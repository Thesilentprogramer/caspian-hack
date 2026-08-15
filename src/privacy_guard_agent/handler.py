from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from privacy_guard.guard import Guard
from privacy_guard.types import MappingExpired
from privacy_guard_agent.llm import Completer, FeatherlessCompleter
from privacy_guard_agent.outbound import to_plain
from privacy_guard_agent.threads import ThreadRoster
from privacy_guard_agent.triage import Decision, triage

_ACK_REPLY = "You're welcome."


def handle_message(
    message: object,
    guard: Guard,
    completer: Completer,
    etiquette: str = "",
    roster: ThreadRoster | None = None,
) -> None:
    decision = triage(message, roster=roster)
    print(f"[privacy-guard] triage={decision}", flush=True)

    if decision is Decision.SKIP:
        return
    if decision is Decision.ACK:
        _ack(message)
        return

    text = getattr(message, "text", None) or ""
    conversation_id = getattr(message, "conversation_id", None)
    typing = getattr(message, "typing", None)
    if callable(typing):
        typing()

    prior = roster.history(conversation_id) if roster else []
    mapping_id = roster.mapping_id(conversation_id) if roster else None
    result = guard.sanitize(text, mapping_id=mapping_id)
    print(f"[privacy-guard] sanitized -> {result.safe_text!r}", flush=True)

    channel = getattr(message, "channel", None)
    try:
        raw = completer.complete(
            result.safe_text,
            channel=channel,
            etiquette=etiquette,
            history=prior,
        )
    except TypeError:
        raw = completer.complete(result.safe_text)
    except Exception as exc:
        print(f"[privacy-guard] completer failed: {exc}", flush=True)
        _reply(
            message,
            "I redacted that message, but the language model call failed. "
            "Check FEATHERLESS_MODEL — Llama 3.x is gated on Featherless.",
        )
        return

    try:
        final = guard.restore(raw, result.mapping_id)
    except MappingExpired:
        _reply(
            message,
            "Sorry — the redaction mapping expired. Please resend your message.",
        )
        return
    _reply(message, to_plain(final))
    if roster and conversation_id:
        roster.append(conversation_id, "user", result.safe_text)
        roster.append(conversation_id, "assistant", to_plain(raw))
        roster.set_mapping_id(conversation_id, result.mapping_id)
        roster.touch(conversation_id)


def _ack(message: object) -> None:
    react = getattr(message, "react", None)
    if callable(react):
        try:
            react("thumbsup")
            return
        except Exception:
            pass
    _reply(message, _ACK_REPLY)


def _reply(message: object, text: str) -> None:
    reply = getattr(message, "reply", None)
    if not callable(reply):
        raise TypeError("message has no reply()")
    reply(text)


def main() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path, override=True)
    from caspian_sdk import CommClient

    username = os.environ.get("CASPIAN_EMAIL_USERNAME", "privacy-guard")
    slack_name = os.environ.get("CASPIAN_SLACK_DISPLAY_NAME", "Privacy Guard")

    client = CommClient()
    inbox = client.connect_email(username=username)
    print(f"Agent email: {inbox['address']}", flush=True)

    slack = client.install_slack(display_name=slack_name)
    authorize = slack.get("authorize_url") if isinstance(slack, dict) else None
    if authorize:
        print(f"Add to Slack: {authorize}", flush=True)
    else:
        print(f"Slack connection: {slack!r}", flush=True)

    guard = Guard()
    completer = FeatherlessCompleter.from_env()
    roster = ThreadRoster()
    print(f"[privacy-guard] completer model -> {completer.model}", flush=True)

    guides: dict[str, str] = {}
    for name in ("slack", "email"):
        try:
            guides[name] = client.channel_guide(name)
        except Exception as exc:
            print(f"[privacy-guard] channel guide {name} unavailable: {exc}", flush=True)
            guides[name] = ""

    @client.on_message
    def _on_message(message: object) -> None:
        channel = (getattr(message, "channel", None) or "slack").lower()
        handle_message(
            message,
            guard,
            completer,
            etiquette=guides.get(channel, ""),
            roster=roster,
        )

    print("Listening on Slack + Email (Ctrl+C to stop).", flush=True)
    try:
        client.listen(concurrency="debounce", debounce_ms=800)
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()

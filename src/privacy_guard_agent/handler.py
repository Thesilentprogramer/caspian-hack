from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from privacy_guard.guard import Guard
from privacy_guard.types import MappingExpired
from privacy_guard_agent.llm import Completer, FeatherlessCompleter


def handle_message(message: object, guard: Guard, completer: Completer) -> None:
    text = getattr(message, "text", None) or ""
    if not text.strip():
        reply = getattr(message, "reply", None)
        if callable(reply):
            reply("I didn't catch any text in that message.")
        return

    typing = getattr(message, "typing", None)
    if callable(typing):
        typing()

    result = guard.sanitize(text)
    print(f"[privacy-guard] sanitized -> {result.safe_text!r}", flush=True)

    raw = completer.complete(result.safe_text)
    try:
        final = guard.restore(raw, result.mapping_id)
    except MappingExpired:
        _reply(
            message,
            "Sorry — the redaction mapping expired. Please resend your message.",
        )
        return
    _reply(message, final)


def _reply(message: object, text: str) -> None:
    reply = getattr(message, "reply", None)
    if not callable(reply):
        raise TypeError("message has no reply()")
    reply(text)


def main() -> None:
    load_dotenv()
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

    @client.on_message
    def _on_message(message: object) -> None:
        handle_message(message, guard, completer)

    print("Listening on Slack + Email (Ctrl+C to stop).", flush=True)
    try:
        client.listen()
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()

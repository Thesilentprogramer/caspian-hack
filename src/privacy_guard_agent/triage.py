from __future__ import annotations

import re
from enum import StrEnum

from privacy_guard._scanner import RegexScanner

_MENTION = re.compile(r"<@[^>]+>")
_ACK = re.compile(
    r"^(?:thanks|thank you|thx|ty|ok|okay|got it|cool|cheers|👍|:\+1:|\+1)$",
    re.IGNORECASE,
)
_BOT_NAMES = {"privacy guard", "privacy-guard"}
_GROUP_CHATS = {"channel", "group"}
_DIRECTED_CHANNELS = {"email", "sms"}

_scanner = RegexScanner()


class Decision(StrEnum):
    SKIP = "skip"
    ACK = "ack"
    COMPLETE = "complete"


def triage(message: object) -> Decision:
    text = (getattr(message, "text", None) or "").strip()
    if not text:
        return Decision.SKIP
    if _is_bot_echo(message):
        return Decision.SKIP

    channel = (getattr(message, "channel", None) or "").lower()
    chat_type = (getattr(message, "chat_type", None) or "").lower()
    has_spans = bool(_scanner.scan(text))
    mentioned = bool(_MENTION.search(text))

    if has_spans:
        return Decision.COMPLETE
    if channel in _DIRECTED_CHANNELS or chat_type == "dm":
        return Decision.ACK if _is_ack(text) else Decision.COMPLETE
    if chat_type in _GROUP_CHATS:
        if mentioned:
            return Decision.ACK if _is_ack(text) else Decision.COMPLETE
        return Decision.SKIP
    # Email and other channels that do not report chat_type.
    return Decision.ACK if _is_ack(text) else Decision.COMPLETE


def _is_ack(text: str) -> bool:
    cleaned = _MENTION.sub("", text).strip().strip(".,!")
    return bool(_ACK.match(cleaned))


def _is_bot_echo(message: object) -> bool:
    sender = getattr(message, "sender", None) or {}
    if not isinstance(sender, dict):
        return False
    if sender.get("is_bot") or sender.get("bot"):
        return True
    name = str(sender.get("name") or sender.get("display_name") or "").strip().lower()
    return name in _BOT_NAMES

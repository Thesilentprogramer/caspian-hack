from __future__ import annotations

import re
from enum import StrEnum

from privacy_guard._scanner import RegexScanner
from privacy_guard.types import Category, categories_from_env
from privacy_guard_agent.threads import ThreadRoster

_MENTION = re.compile(r"<@[^>]+>")
_ACK = re.compile(
    r"^(?:thanks|thank you|thx|ty|ok|okay|got it|cool|cheers|👍|:\+1:|\+1)$",
    re.IGNORECASE,
)
_BOT_NAMES = {"privacy guard", "privacy-guard"}
_GROUP_CHATS = {"channel", "group"}
_DIRECTED_CHANNELS = {"email", "sms", "telegram"}


class Decision(StrEnum):
    SKIP = "skip"
    ACK = "ack"
    COMPLETE = "complete"


def triage(
    message: object,
    roster: ThreadRoster | None = None,
    *,
    categories: frozenset[Category] | None = None,
) -> Decision:
    text = (getattr(message, "text", None) or "").strip()
    if not text:
        return Decision.SKIP
    if _is_bot_echo(message):
        return Decision.SKIP

    channel = (getattr(message, "channel", None) or "").lower()
    chat_type = (getattr(message, "chat_type", None) or "").lower()
    conversation_id = getattr(message, "conversation_id", None)
    allowed = categories if categories is not None else categories_from_env()
    has_spans = bool(RegexScanner(allowed=allowed).scan(text))
    mentioned = bool(_MENTION.search(text))
    warm = bool(roster and roster.is_warm(conversation_id))

    if has_spans:
        return Decision.COMPLETE
    if channel in _DIRECTED_CHANNELS or chat_type == "dm":
        return Decision.ACK if _is_ack(text) else Decision.COMPLETE
    if chat_type in _GROUP_CHATS:
        if mentioned or warm:
            return Decision.ACK if _is_ack(text) else Decision.COMPLETE
        return Decision.SKIP
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

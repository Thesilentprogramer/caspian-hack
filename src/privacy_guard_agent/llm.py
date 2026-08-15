from __future__ import annotations

import os
from typing import Protocol

from openai import OpenAI

FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
# Llama 3.x is HuggingFace-gated on Featherless. Qwen is the documented ungated default.
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

SYSTEM_PROMPT = (
    "You are a helpful support agent answering on Slack and Email. "
    "Never use Markdown. Do not use asterisks, **bold**, __underline__, "
    "or # headings. Write plain sentences. Numbered lists use 1. 2. 3. "
    "The user message may contain typed placeholders such as [IP_ADDRESS_F5BA] "
    "or [API_KEY_9C1D]. Copy every placeholder into your reply verbatim — "
    "do not invent, alter, expand, or omit them. Treat them as the real values."
)

_SLACK_ETIQUETTE = (
    "This message is on Slack. Keep the reply short. Use short paragraphs. No subject line."
)
_EMAIL_ETIQUETTE = (
    "This message is email. Start with a short greeting, then short paragraphs. "
    "No Markdown. No subject line inside the body."
)


class Completer(Protocol):
    def complete(
        self,
        text: str,
        channel: str | None = None,
        etiquette: str = "",
        history: list[dict[str, str]] | None = None,
    ) -> str: ...


class FeatherlessCompleter:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = FEATHERLESS_BASE_URL,
        client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self._client = client or OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_env(cls) -> FeatherlessCompleter:
        api_key = os.environ.get("FEATHERLESS_API_KEY", "")
        if not api_key:
            raise RuntimeError("FEATHERLESS_API_KEY is not set")
        model = os.environ.get("FEATHERLESS_MODEL", DEFAULT_MODEL)
        base_url = os.environ.get("FEATHERLESS_BASE_URL", FEATHERLESS_BASE_URL)
        return cls(api_key=api_key, model=model, base_url=base_url)

    def complete(
        self,
        text: str,
        channel: str | None = None,
        etiquette: str = "",
        history: list[dict[str, str]] | None = None,
    ) -> str:
        system = SYSTEM_PROMPT
        if (channel or "").lower() == "email":
            system = f"{system} {_EMAIL_ETIQUETTE}"
        else:
            system = f"{system} {_SLACK_ETIQUETTE}"
        if etiquette.strip():
            system = f"{system}\n\n{etiquette.strip()}"
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for turn in history or []:
            role = turn.get("role") or "user"
            if role not in {"user", "assistant"}:
                role = "user"
            messages.append({"role": role, "content": turn.get("content") or ""})
        messages.append({"role": "user", "content": text})
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        content = response.choices[0].message.content
        return content or ""


class FakeCompleter:
    """Echoes Safe Text so tests can assert Placeholders survived the Completer."""

    def __init__(self) -> None:
        self.seen: list[str] = []
        self.channels: list[str | None] = []
        self.histories: list[list[dict[str, str]]] = []

    def complete(
        self,
        text: str,
        channel: str | None = None,
        etiquette: str = "",
        history: list[dict[str, str]] | None = None,
    ) -> str:
        self.seen.append(text)
        self.channels.append(channel)
        self.histories.append(list(history or []))
        return f"I can help with: {text}"

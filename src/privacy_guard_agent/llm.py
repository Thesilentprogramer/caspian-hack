from __future__ import annotations

import os
from typing import Protocol

from openai import OpenAI

FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"

SYSTEM_PROMPT = (
    "You are a helpful support agent answering on Slack and Email. "
    "The user message may contain typed placeholders such as [IP_ADDRESS_F5BA] "
    "or [API_KEY_9C1D]. Copy every placeholder into your reply verbatim — "
    "do not invent, alter, expand, or omit them. Treat them as the real values."
)


class Completer(Protocol):
    def complete(self, text: str) -> str: ...


class FeatherlessCompleter:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = FEATHERLESS_BASE_URL,
        client: OpenAI | None = None,
    ) -> None:
        self._model = model
        self._client = client or OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_env(cls) -> FeatherlessCompleter:
        api_key = os.environ.get("FEATHERLESS_API_KEY", "")
        if not api_key:
            raise RuntimeError("FEATHERLESS_API_KEY is not set")
        model = os.environ.get("FEATHERLESS_MODEL", DEFAULT_MODEL)
        base_url = os.environ.get("FEATHERLESS_BASE_URL", FEATHERLESS_BASE_URL)
        return cls(api_key=api_key, model=model, base_url=base_url)

    def complete(self, text: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content
        return content or ""


class FakeCompleter:
    """Echoes Safe Text so tests can assert Placeholders survived the Completer."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def complete(self, text: str) -> str:
        self.seen.append(text)
        return f"I can help with: {text}"

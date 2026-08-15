# Privacy Guard

**A local redaction layer that lets an AI agent live in your real channels
without leaking what's in them.**

Built for the Caspian Buildathon — an agent that runs on **Slack + Email**
via [caspian-sdk](https://github.com/TryCaspian/caspian-sdk), wrapped with a
privacy middleware that strips sensitive data out before it ever reaches an
LLM, and puts it back before the reply goes out.

Also ships as a standalone **MCP server**, so the same `sanitize` /
`restore` tools work from any MCP-capable client, not just this agent.

---

## Why

Enterprises want agents inside Slack, email, and SMS — that's where the
actual work is. But routing those messages through a cloud LLM means every
internal IP, API key, customer email, and name in that message leaves the
building too. That's the #1 reason companies stall on connecting LLMs to
real communication tools.

Privacy Guard is the layer that removes that objection: the LLM only ever
sees typed placeholders, never the real values.

```
"having trouble connecting to 192.168.1.105 with key sk_live_abc123"
                          │
                          ▼  sanitize()
"having trouble connecting to [IP_ADDRESS_F5BA] with key [API_KEY_9C1D]"
                          │
                          ▼  (this is all the LLM ever sees)
                     LLM reasons, replies
                          │
                          ▼  restore()
"having trouble connecting to 192.168.1.105 with key sk_live_abc123"
```

**What this is:** local tokenization with key custody — a standard,
established pattern (same category as Microsoft Presidio).
**What this is not:** a cryptographic zero-knowledge proof. We don't use
that term for this, and neither should you if you read this.

---

## How it works

1. `sanitize(text)` — regex + NER scan finds sensitive spans, encrypts each
   value locally (Fernet / AES-128-CBC + HMAC), replaces it with a typed
   placeholder like `[EMAIL_A1B2]`, and returns the safe text plus a
   `mapping_id`. The encrypted values live only in an in-memory, TTL-bound
   store — never written to disk, never sent anywhere.
2. The safe text goes to Featherless. Featherless never sees a raw value, but
   because placeholders are *typed*, it still reasons coherently about them.
3. `restore(text, mapping_id)` — decrypts and substitutes the real values
   back into the LLM's response, right before `message.reply()` sends it.

```
Incoming (Slack / Email)
       │
       ▼
[Caspian on_message handler]
       │
       ▼
  sanitize() ──► regex: email / IP / credit card / API key / phone
       │         spaCy NER: person / org names
       ▼
  [safe text only] ──► Featherless (OpenAI-compatible)
       │
       ▼
  restore() ──► real values re-injected
       │
       ▼
  message.reply()  →  back out on Slack / Email
```

The Completer is **not** streamed. Restore needs the full reply; streaming
would leak placeholders onto the channel.

---

## What's detected

| Category | Method | Reliability |
|---|---|---|
| Email addresses | Regex | High |
| IP addresses | Regex | High |
| Credit card numbers | Regex (Luhn-checked) | High |
| API-key-shaped strings | Regex (common prefixes: `sk_`, `pk_`, `ghp_`, etc.) | High |
| Phone numbers | Regex | High |
| Person / org names | spaCy NER (`en_core_web_sm`) | Best-effort — not exhaustive, and we say so |

---

## Project structure

```
caspian-hack/
├── CONTEXT.md
├── pyproject.toml
├── src/
│   ├── privacy_guard/          # deep module: sanitize / restore
│   │   ├── guard.py
│   │   ├── _scanner.py         # regex + NER (private)
│   │   └── _mapping.py         # in-memory Fernet Mapping (private)
│   ├── privacy_guard_mcp/      # Tool Adapter (stdio)
│   └── privacy_guard_agent/    # Channel Adapter + Featherless Completer
├── tests/
├── PRD (1).md
└── README.md
```

Public interface of Privacy Guard is only `sanitize` / `restore`. The Caspian
handler and the MCP server are adapters on that interface.

---

## Setup

```bash
# 1. Python env
uv sync --extra dev
uv run python -m spacy download en_core_web_sm   # optional; NER tests skip without it

# 2. Env
cp .env.example .env
# CASPIAN_API_KEY — mint one:
curl -s -X POST https://api.trycaspianai.com/v1/projects/sandbox \
  -H 'Content-Type: application/json' -d '{"name":"privacy-guard"}'
# FEATHERLESS_API_KEY — from featherless.ai (hackathon inference partner)
# FEATHERLESS_MODEL=Qwen/Qwen2.5-7B-Instruct   # Llama 3.x is HuggingFace-gated
# After changing .env, restart the agent — it only reads the model at startup.

# 3. Tests (no live channels, no spaCy model)
uv run pytest -m "not live and not ner"

# 4. Agent — Slack + Email, Featherless wrapped in the Guard
uv run privacy-guard-agent

# 5. MCP — Cursor loads .cursor/mcp.json in this repo.
# Do not run `uv run privacy-guard-mcp` in a normal terminal (stdio JSON-RPC).
# Inspector (optional):
uv run mcp dev src/privacy_guard_mcp/server.py
```

Project MCP config is [`.cursor/mcp.json`](.cursor/mcp.json). Reload Cursor MCP servers after clone. The agent only calls the Completer for email, Slack DMs, @mentions, or messages that already contain Sensitive Spans. Channel chatter and "thanks" do not spend tokens.

### Why Featherless

Featherless.ai is this hackathon's inference partner — every participant gets
a free plan, so the "LLM" in the middle of the sanitize/restore round trip
runs on Featherless, not a bring-your-own API key. It's OpenAI-compatible
(same `/v1/chat/completions` shape, just a different `base_url` + model ID),
so swapping providers later is a one-line change, not a rewrite.

---

## Demo flow

1. Message the agent on **Slack**: *"having trouble connecting to
   192.168.1.105 with key sk_live_abc123, can you help Rohan out?"*
2. Terminal shows the **sanitized** text — the actual string sent to
   Featherless — with placeholders in place of the real values.
3. The reply comes back on Slack (or you message it on **Email** instead —
   same handler, same result) with the real values correctly restored.
4. Open an MCP client, call `sanitize` directly on a new string, to show
   the tool works independent of the Caspian wiring — it's a real,
   reusable MCP server, not glue code bolted to one handler.

---

## Honest limitations

- Name/entity detection is NER-based and **will miss edge cases** — this is
  disclosed on purpose, not discovered by a judge mid-demo.
- The mapping store is in-memory only. Restart the process and old mappings
  are gone — by design, this is not meant to be a persistent vault.
- This protects text content only — no attachments, no OCR, no database
  connectors.
- Encryption is a standard, audited library (Fernet: AES-128-CBC +
  HMAC-SHA256) — not custom crypto, and not "zero-knowledge" in the
  cryptographic sense of that term.

---

## Built with

[caspian-sdk](https://github.com/TryCaspian/caspian-sdk) · Python ·
[cryptography](https://cryptography.io/) (Fernet) · [spaCy](https://spacy.io/)
· [MCP](https://modelcontextprotocol.io/) ·
[Featherless](https://featherless.ai)

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
2. The safe text goes to the LLM. The LLM never sees a raw value, but
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
  [safe text only] ──► LLM
       │
       ▼
  restore() ──► real values re-injected
       │
       ▼
  message.reply()  →  back out on Slack / Email
```

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
caspian-privacy-guard/
├── detector.py        # regex + NER scanning
├── vault.py            # in-memory encrypted mapping store (TTL)
├── guard.py            # sanitize() / restore(), the public API
├── mcp_server.py        # exposes sanitize/restore as MCP tools (stdio)
├── agent_handler.py     # caspian-sdk on_message handler, Slack + Email
├── requirements.txt
├── PRD.md
└── README.md
```

---

## Setup

```bash
# 1. Python deps
pip install caspian-sdk cryptography spacy mcp openai --break-system-packages
python -m spacy download en_core_web_sm

# 2. Caspian project + API key
curl -s -X POST https://api.trycaspianai.com/v1/projects/sandbox \
  -H 'Content-Type: application/json' -d '{"name":"privacy-guard"}'
# write the returned api_key to .env as CASPIAN_API_KEY

# 3. Featherless.ai API key (hackathon inference partner — free $25 plan)
# get a key from featherless.ai, write it to .env as:
#   FEATHERLESS_API_KEY=...
#   FEATHERLESS_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct   # or any model from /v1/models

# 4. Run the agent (connects Slack + Email, wraps Featherless calls in the guard)
python agent_handler.py

# 5. Run the MCP server standalone (for use from Claude Desktop / Cursor / etc.)
python mcp_server.py
```

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
2. Terminal shows the **sanitized** text — the actual string sent to the
   LLM — with placeholders in place of the real values.
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
· [MCP](https://modelcontextprotocol.io/)
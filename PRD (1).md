# PRD: Privacy Guard — a redaction layer for agents on real channels

**Project for:** Caspian Buildathon (15-Day AI Agent Hackathon)
**Status:** Draft — build night
**Owner:** [your name]

---

## 1. Problem

Companies want AI agents inside their real communication channels — Slack,
email, SMS, WhatsApp — because that's where work actually happens. But the
moment a message from an internal channel gets forwarded to a cloud LLM,
whatever's in that message (an internal IP, a customer email, an API key, a
person's name, a credit card fragment) leaves the building. This is a widely
cited reason enterprises stall or block LLM adoption on their communication
tools: the model provider becomes a new, uncontrolled place where sensitive
data lives.

Most teams solve this by not solving it — they just don't connect sensitive
channels to LLMs at all, or they self-host a model (expensive, slower, still
requires trust in infra).

## 2. Solution

**Privacy Guard** is a small, local middleware layer that sits between a
Caspian-connected channel and the LLM. It:

1. Scans outbound-to-LLM text for sensitive spans (emails, IPs, API keys,
   credit card numbers, phone numbers, person/org names).
2. Replaces each span with a typed, reversible placeholder token
   (e.g. `[EMAIL_A1B2]`, `[IP_ADDRESS_F5BA]`), and holds the real value in an
   in-memory, TTL-bound map — never persisted, never sent anywhere.
3. Lets the LLM reason over the safe, structurally-intact text. Because
   placeholders are typed, the LLM's output stays logically coherent
   (e.g. "please whitelist `[IP_ADDRESS_F5BA]`").
4. Restores the real values into the LLM's response text immediately before
   `message.reply()` sends it back out on the real channel.

The LLM provider never sees raw sensitive data. The mapping never leaves the
local process. This is **not** a cryptographic zero-knowledge proof — it's a
local redaction/tokenization proxy, the same category of technique used by
tools like Microsoft Presidio, applied specifically at the boundary of a
Caspian-connected agent.

It ships two ways:
- **As an MCP server** (`sanitize` / `restore` tools) — reusable by any
  MCP-capable client, not just this project.
- **Wired into a Caspian agent handler** running on two real channels
  (Slack + Email for the demo), to satisfy the buildathon's channel rule and
  prove it works on live traffic, not a mocked example.

## 3. Goals (this build)

| Goal | Success looks like |
|---|---|
| Detect the common sensitive categories | Regex catches emails, IPs, credit cards, API-key-shaped strings, phone numbers reliably |
| Detect names without a fixed pattern | spaCy NER catches person/org names in ordinary sentences (accepted: not 100%, must be demoed honestly) |
| Round-trip fidelity | Every placeholder sent to the LLM is restored correctly, byte-for-byte, in the final outbound message |
| Real channel proof | The same handler answers correctly on **two** live Caspian channels (Slack + Email) with redaction active on both |
| MCP reusability | The `sanitize`/`restore` tools work when called directly via MCP from a separate client (e.g. Claude Desktop), not just from the Caspian handler |

## 4. Non-goals (explicitly out of scope tonight)

- Not a cryptographic zero-knowledge proof system — no claim of provable
  privacy, just local custody of the mapping.
- Not persistent storage / audit logging of redacted data (mapping is
  in-memory, TTL-expired, gone on restart — by design, not a limitation to
  hide).
- Not 100% recall on name/entity detection — NER has known false
  negatives; we say so out loud in the demo rather than overclaiming.
- Not building custom crypto — using a standard, audited library
  (`cryptography`'s Fernet, which is AES-128-CBC + HMAC) rather than
  hand-rolling anything.
- Not handling every enterprise data type (no OCR, no attachment scanning,
  no database connectors) — text messages only.

## 5. Users / who this is for

- **Primary demo persona:** an engineering team using a Slack+Email-connected
  support agent, where messages routinely contain internal IPs, staging
  credentials, and customer PII that shouldn't reach a third-party LLM
  provider unfiltered.
- **Real-world buyer (framing, not built tonight):** any company evaluating
  "can we point an LLM agent at our internal channels" — this layer is the
  answer to their first objection.

## 6. How it works (architecture)

```
Incoming message (Slack / Email, via caspian-sdk on_message)
        │
        ▼
 sanitize(text) ──► regex + spaCy NER scan
        │            │
        │            ├─► sensitive span found
        │            │     → encrypt value locally (Fernet)
        │            │     → replace with typed placeholder [TYPE_XXXX]
        │            │     → store {placeholder: encrypted value} in memory
        │            ▼
        │      safe_text, mapping_id
        ▼
   LLM call (safe_text only — no raw sensitive data ever sent)
        │
        ▼
   llm_response (contains placeholders, logically coherent)
        │
        ▼
 restore(llm_response, mapping_id) ──► decrypt + substitute real values back
        │
        ▼
   message.reply(final_text)  → sent on the real channel (Slack / Email)
```

### Components

| Component | What it does |
|---|---|
| `detector.py` | Regex rules (email, IP, credit card, API key shape, phone) + spaCy NER (person, org) |
| `vault.py` | In-memory `{placeholder_id: Fernet-encrypted value}` store with TTL expiry |
| `guard.py` | `sanitize(text) -> (safe_text, mapping_id)` and `restore(text, mapping_id) -> real_text` |
| `mcp_server.py` | Exposes `sanitize` / `restore` as MCP tools over stdio |
| `agent_handler.py` | Caspian `on_message` handler: connects Slack + Email, calls `guard` around the LLM call |

**Inference provider:** [Featherless.ai](https://featherless.ai) — this
hackathon's official inference partner (free plan for all participants). The
LLM call inside `agent_handler.py` targets Featherless's OpenAI-compatible
endpoint (`https://api.featherless.ai/v1/chat/completions`), so the sanitized
text is what actually crosses the wire to Featherless, and the restore step
happens on what comes back. This is a deliberate, load-bearing part of the
architecture — the redaction boundary matters precisely because we're calling
a third-party inference provider rather than a self-hosted model.

## 7. MCP tool surface

```jsonc
// tool: sanitize
{
  "name": "sanitize",
  "input": { "text": "string" },
  "output": { "safe_text": "string", "mapping_id": "string" }
}

// tool: restore
{
  "name": "restore",
  "input": { "text": "string", "mapping_id": "string" },
  "output": { "restored_text": "string" }
}
```

Kept deliberately to two tools. No third tool added just to look more
complete — a small, correct surface is the point.

## 8. Demo script (for judges)

1. Show the Slack-connected agent and the Email-connected agent — same
   process, same `on_message` handler (proves the caspian-sdk requirement).
2. Send a message containing a fake staging IP, an API key, and a name:
   *"Hey, having trouble connecting to 192.168.1.105 with key sk_live_abc123,
   can you help Rohan out?"*
3. Show the terminal logging the **sanitized** version actually sent to the
   LLM — the raw values are visibly absent.
4. Show the final reply on Slack/Email has the real values correctly
   restored.
5. Open Claude Desktop (or another MCP client), call `sanitize` directly on
   a new string live, to prove it's a real, reusable MCP tool — not just
   glue code inside one handler.
6. State the honest caveat: name detection is NER-based and not perfect —
   show one example it catches and be upfront that edge cases exist.

## 9. Risks / honesty checklist

- [ ] Do not call this "zero-knowledge" out loud or in writing — it's local
      tokenization with key custody, a different (still legitimate) thing.
- [ ] Do not claim AES-256 — Fernet is AES-128-CBC + HMAC-SHA256. State it
      correctly if asked.
- [ ] Do not claim comprehensive PII coverage — state clearly what's regex
      (reliable) vs NER (best-effort).
- [ ] Mapping is in-memory only — say this proactively, don't wait to be
      asked "where do you store the real values."

## 10. Build plan (tonight)

1. `detector.py` — regex rules, then spaCy NER for names (30–45 min)
2. `vault.py` — Fernet encrypt/decrypt + in-memory dict + TTL (20 min)
3. `guard.py` — glue `sanitize`/`restore` (20 min)
4. `mcp_server.py` — wrap as MCP tools over stdio (30–45 min)
5. `agent_handler.py` — caspian-sdk `on_message`, connect Slack + Email,
   call guard around the LLM call (45–60 min)
6. End-to-end test: real Slack message → redacted LLM call → correct
   restored reply (30 min)
7. Record demo video, write final README (30–45 min)
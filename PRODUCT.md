# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

static HTML/CSS (confirmed in the deploy plan: no React, no Flask; open as a file or GitHub Pages)

## Users

Hackathon judges and engineers wiring an agent to real communication channels. They evaluate whether an LLM can sit on Slack, Email, or Telegram without seeing secrets.

## Product Purpose

Privacy Guard is a local redaction layer. It Sanitizes a Channel Message into Safe Text plus a Mapping Id, lets a Completer reason over Placeholders only, then Restores real values before `message.reply()`. Success is: the Completer never receives raw Sensitive Spans, and the human still gets a usable reply.

## Positioning

Typed Placeholders (`[IP_ADDRESS_…]`, `[API_KEY_…]`) so the Completer can still reason, with Fernet Mapping that lives only in process memory. This is not a cryptographic zero-knowledge proof. A neighboring PII API that ships values to the cloud cannot truthfully copy “the Mapping never leaves this laptop.”

## Operating Context

- Channel Adapter: Caspian `on_message` on Slack, Email, and optional Telegram (`TELEGRAM_BOT_TOKEN`).
- Completer: Featherless (OpenAI-compatible). Default documented model is Qwen; this clone may set `FEATHERLESS_MODEL`.
- Tool Adapter: MCP stdio (`sanitize`, `restore`, `redaction_report`). Cursor loads `.cursor/mcp.json`. Do not run the MCP server in a normal terminal.
- Operate dashboard: `http://127.0.0.1:8787` in the agent process (counts, never values).
- Category Allowlist: `PRIVACY_GUARD_CATEGORIES`. Unset = all seven; empty = redact nothing.

## Capabilities and Constraints

- Categories: EMAIL, IP_ADDRESS, CREDIT_CARD, API_KEY, PHONE, PERSON, ORG. Regex is deterministic; PERSON/ORG are best-effort spaCy NER.
- Mapping is in-memory, TTL-bound, gone on restart. Fernet: AES-128-CBC + HMAC-SHA256.
- Text only. No attachments, no OCR, no database connectors.
- MCP Mapping and agent Mapping are separate processes (no shared store).
- Public remote MCP is out of scope: it would host someone else’s Mapping.

## Brand Commitments

Name: Privacy Guard. Glossary in `CONTEXT.md` is binding (Sanitize, Restore, Placeholder, Mapping, Channel Message — not tokenizer, not zero-knowledge layer). Slack display name: Privacy Guard. Email: `privacy-guard@agents.trycaspianai.com`. Optional Telegram: `@CaspianPrivacyGuardBot` when a bot token is set.

## Evidence on Hand

- Demo sentence: `having trouble connecting to 192.168.1.105 with key sk_live_abc123, can you help Rohan out?`
- Live checks: Slack workspace `shubham`, Email roundtrip with restore, Telegram connection when token is set.
- No customer logos, testimonials, pricing, or third-party case studies. Do not fabricate them.

## Product Principles

1. Secrets stay on the laptop. Mapping never goes to disk or to the Completer.
2. Typed Placeholders over opaque blobs so the Completer can still work.
3. Honest limits: NER misses, in-memory Mapping, text-only.
4. Two adapters, one Guard: Channel Adapter and Tool Adapter both call Sanitize/Restore.
5. Show the work: Redaction Report counts, dashboard hero of values kept off Featherless — never the values.

## Accessibility & Inclusion

WCAG contrast ≥4.5:1 on the landing. Honor `prefers-reduced-motion` and `prefers-reduced-transparency`. Keyboard-reachable primary actions.

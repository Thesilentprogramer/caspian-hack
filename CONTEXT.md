# Privacy Guard

A local redaction context: Channel Messages are tokenized before they reach an LLM, and restored before they go back out on a channel.

## Language

**Privacy Guard**:
The local redaction module that sits between a Channel Message and an LLM.
_Avoid_: privacy middleware, PII service, tokenizer, zero-knowledge layer

**Channel Message**:
Inbound text from a real communication channel (Slack or Email in this product).
_Avoid_: request, prompt, payload

**Sensitive Span**:
A substring of a Channel Message classified as a Category.
_Avoid_: PII, entity, match, token

**Category**:
The kind of a Sensitive Span: Email, IP Address, Credit Card, API Key, Phone, Person, or Org.
_Avoid_: type, label, PII type

**Placeholder**:
A typed stand-in for a Sensitive Span, e.g. `[EMAIL_A1B2]`.
_Avoid_: token, mask, redaction tag

**Safe Text**:
Text that contains Placeholders and no raw Sensitive Spans.
_Avoid_: sanitized string, redacted prompt, scrubbed text

**Mapping**:
The TTL-bound, Fernet-encrypted table of Placeholder → real value, identified by a Mapping Id. It lives only in process memory.
_Avoid_: vault, store, cache, key-value

**Mapping Id**:
The identifier that pairs a Sanitize call with its later Restore.
_Avoid_: session id, vault id, key

**Sanitize**:
The operation that turns a Channel Message into Safe Text plus a Mapping Id.
_Avoid_: redact, mask, scrub, tokenize

**Restore**:
The operation that substitutes real values back into text that still contains Placeholders, using a Mapping Id.
_Avoid_: decrypt, detokenize, unmask

**Scanner**:
The finder of Sensitive Spans: a Regex Scanner (deterministic) and an optional NER Scanner (best-effort names).
_Avoid_: detector, extractor, recognizer

**Completer**:
The LLM call that receives only Safe Text and returns a reply that may still contain Placeholders.
_Avoid_: model, inference provider (when you mean the seam)

**Channel Adapter**:
The Caspian `on_message` handler that Sanitizes, calls the Completer, Restores, then replies on Slack and Email.
_Avoid_: agent handler, bot, service

**Tool Adapter**:
The MCP server that exposes Sanitize and Restore as two tools.
_Avoid_: MCP service, API

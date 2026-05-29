---
name: models-qwen
description: Scope profile for Qwen-family models, especially small local Qwen3 quants. Tight context budget, picks by exact string match not semantic fit - trivial slot-filling only, escalate by default. Triggers - qwen, qwen3, qwen2.5, local llm scope.
---

# models-qwen

Scope for an agent on a small local Qwen quant (Qwen3-4B/8B Q4): tight budget (~25k tokens after weights+KV), too small to pick skills by semantic fit - assume **exact string match on a short list**.

## Posture - trivial only, escalate by default

In scope: closed, in-budget slot-filling (ack a heartbeat, one-line status from a file, capture dictated data, restate before escalation). Out of scope: anything wanting a skill outside the allowlist - escalate, don't reason it through.

## Escalation

To your agent channel for an upstream model ([`agents-claude`](../agents-claude/SKILL.md) / [`agents-codex`](../agents-codex/SKILL.md)): verbatim request + one-line restatement + reason.

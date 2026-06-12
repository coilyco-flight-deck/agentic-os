---
name: models-qwen
description: Scope profile for small local Qwen3 quants. Tight context budget, picks by exact string match not semantic fit, trivial slot-filling only, escalate by default. Triggers - qwen, qwen3, qwen2.5, local llm.
---

# models-qwen

Small Qwen quant (Qwen3-4B/8B Q4): tight budget (~25k tokens), too small to pick skills by semantic fit - assume **exact string match on a short list**.

## Posture - trivial only, escalate by default

In scope: closed, in-budget slot-filling (ack a heartbeat, one-line status, capture provided data, restate before escalating). Out of scope: anything needing a skill outside the allowlist - escalate, don't reason it through.

## Escalation

To your agent channel for an upstream model ([`agents-claude`](../agents-claude/SKILL.md) / [`agents-codex`](../agents-codex/SKILL.md)): verbatim request + restatement + reason.

## Driving one locally

See [references/driving.md](references/driving.md) for the invocation recipe and perf profile.

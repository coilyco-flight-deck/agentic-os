---
name: models-qwen-coder
description: Capable local-coder tier - Qwen3 30B-A3B on Ollama. Real in-repo coding, not trivial-only; escalate only for cloud-grade judgment. Triggers - qwen3-coder, qwen coder, 30b coder, local coder.
---

# models-qwen-coder

Capable local tier: Qwen3 30B-A3B at Q4 (`qwen3-coder:30b` coder, `qwen3:30b-a3b` general) on Ollama, 32k context, tool use. The rung between [`models-qwen`](../models-qwen/SKILL.md) (trivial 4B/8B) and cloud [`agents-claude`](../agents-claude/SKILL.md) / [`agents-codex`](../agents-codex/SKILL.md).

## Posture - real local work, selective escalation

Does genuine in-repo coding: multi-file edits, tool use, short-list skill pick. **Not** escalate-by-default. Escalate up only for cloud-grade judgment, large-context reasoning, or privileged ops.

## Related

- Driven by [`agents-opencode`](../agents-opencode/SKILL.md) / [`agents-aider`](../agents-aider/SKILL.md) / [`agents-goose`](../agents-goose/SKILL.md). Wants a 24GB-class GPU.

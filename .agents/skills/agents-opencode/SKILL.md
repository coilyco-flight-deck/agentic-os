---
name: agents-opencode
description: Harness profile for OpenCode - a TUI/CLI harness floating over swappable models (local Qwen today). Pronouns they/them. Capability ceiling is the active models-* profile, not the harness. Triggers - opencode, qwen-opencode.
---

# agents-opencode

The **OpenCode** harness (they/them). It **floats over swappable models**, so the model is the real distinguisher and the ceiling is the active [`models-*`](../models-qwen/SKILL.md) profile, not "OpenCode". Today it runs a local Qwen quant via Ollama - the `qwen-opencode` agent.

Unlike [`agents-claude`](../agents-claude/SKILL.md) / [`agents-codex`](../agents-codex/SKILL.md) (fixed cloud models), OpenCode-on-Qwen is small and local: trivial-only, escalate by default ([`models-qwen`](../models-qwen/SKILL.md)). Its global context is the aos-public base alone - no private context, no skill catalog.

## Related

- `agents-claude`, `agents-codex` - sibling cloud harnesses, the escalation targets.

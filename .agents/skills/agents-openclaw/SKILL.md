---
name: agents-openclaw
description: Harness profile for OpenClaw - the harness that floats over swappable models (Qwen today, more incoming). Pronouns they/them. Its capability ceiling is set by the active models-* profile, not the harness. Triggers - openclaw, open claw.
---

# agents-openclaw

The **OpenClaw** harness (they/them). Unlike [`agents-claude`](../agents-claude/SKILL.md) / [`agents-codex`](../agents-codex/SKILL.md) (bound to a fixed cloud model), OpenClaw **floats over swappable models** - so the model name is the meaningful distinguisher and the capability ceiling is the active [`models-*`](../models-qwen/SKILL.md) profile, not "OpenClaw".

- Small local model → inherit its scope ([`models-qwen`](../models-qwen/SKILL.md): trivial-only, escalate by default).
- Larger model → more capable, per that profile.

## Related

- `tooling-openclaw-workspace` - workspace mechanics.
- `agents-claude`, `agents-codex` - sibling harnesses.

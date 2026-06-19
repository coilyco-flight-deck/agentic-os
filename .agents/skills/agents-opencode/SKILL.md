---
name: agents-opencode
description: Harness profile for OpenCode - a TUI/CLI harness floating over swappable models (local Qwen today). Pronouns they/them. Capability ceiling is the active models-* profile, not the harness. Triggers - opencode, qwen-opencode.
---

# agents-opencode

The **OpenCode** harness (they/them). It **floats over swappable models**, so the model is the ceiling, not "OpenCode" - the active `models-*` profile. **Reach for it when** you want a general interactive local-coding session - the default of the three floaters.

Two tiers: on the capable coder (`models-qwen-coder`) it does real in-repo work; as the confined `qwen-opencode` agent on the trivial tier (`models-qwen`) it is trivial-only, escalate by default, aos-public base alone.

## Related

- `agents-claude`, `agents-codex` - cloud escalation targets. `agents-aider`, `agents-goose` - sibling floaters.

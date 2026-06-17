---
name: agents-aider
description: Harness profile for Aider, a git-native pair-programming CLI floating over swappable models (cloud or local Ollama). Triggers - aider, aider-chat.
---

# agents-aider

The **Aider** harness - a git-native pair-programming CLI (`aider-chat`). Harness axis, orthogonal to the [`models-*`](../models-qwen/SKILL.md) capability axis: like [`agents-opencode`](../agents-opencode/SKILL.md) it floats over swappable models, so the active model is the ceiling, not "Aider". Binds to a cloud model or a local Ollama quant.

## Posture

- Edit-by-diff in a git repo: reads files, makes targeted edits, commits each. Drive it from inside a repo.
- Ceiling is the bound model: a small local quant ([`models-qwen`](../models-qwen/SKILL.md)) or a peer cloud model.

## Related

- `agents-claude`, `agents-codex`, `agents-opencode`, `agents-goose` - sibling harnesses. `models-qwen` - capability axis.

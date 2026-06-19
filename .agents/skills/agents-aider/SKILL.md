---
name: agents-aider
description: Harness profile for Aider, a git-native pair-programming CLI floating over swappable models (cloud or local Ollama). Triggers - aider, aider-chat.
---

# agents-aider

The **Aider** harness (they/them) - a git-native pair-programming CLI (`aider-chat`). Harness axis, orthogonal to the `models-*` capability axis: like [`agents-opencode`](../agents-opencode/SKILL.md) it floats over swappable models, so the active model is the ceiling, not "Aider". Binds to a cloud model or a local Ollama quant.

## Posture

- **Reach for it when** the edit is surgical and you can name the files: diff-by-diff in a git repo, one commit per change. The scalpel of the three floaters.
- Ceiling is the bound model: capable local coder (`models-qwen-coder`) or a cloud peer.

## Related

- `agents-claude`, `agents-codex`, `agents-opencode`, `agents-goose` - siblings. `models-qwen-coder` - capability axis.

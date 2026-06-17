---
name: agents-goose
description: Harness profile for Goose, Block's extensible agent floating over swappable models, cloud or local Ollama. Triggers - goose, block goose.
---

# agents-goose

The **Goose** harness (she/her) - Block's open-source agent (`goose` CLI plus desktop app), built on MCP extensions and recipes. Harness axis, orthogonal to the [`models-*`](../models-qwen/SKILL.md) capability axis: it floats over many providers, so the active model is the ceiling, not "Goose". Binds to a cloud model or a local Ollama quant.

## Posture

- **Reach for it when** the task is a multi-step loop needing tool use: MCP extensions/recipes, more autonomy than a pair-programmer. Provider + model in `config.yaml`; env overrides it.
- Ceiling is the bound model: capable local coder ([`models-qwen-coder`](../models-qwen-coder/SKILL.md)) or a cloud peer.

## Related

- `agents-claude`, `agents-codex`, `agents-aider`, `agents-opencode` - siblings. `models-qwen-coder` - capability axis.

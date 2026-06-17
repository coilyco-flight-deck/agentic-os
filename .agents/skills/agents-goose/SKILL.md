---
name: agents-goose
description: Harness profile for Goose, Block's extensible agent (MCP extensions, recipes) floating over swappable models, cloud or local Ollama. Triggers - goose, block goose.
---

# agents-goose

The **Goose** harness - Block's open-source agent (`goose` CLI plus desktop app), built on MCP extensions and recipes. Harness axis, orthogonal to the [`models-*`](../models-qwen/SKILL.md) capability axis: it floats over many providers, so the active model is the ceiling, not "Goose". Binds to a cloud model or a local Ollama quant.

## Posture

- Multi-step agentic loop with MCP-extension tool use, heavier than a pair-programmer. Provider plus model in `config.yaml`; env overrides it.
- Ceiling is the bound model: a small local quant ([`models-qwen`](../models-qwen/SKILL.md)) or a capable cloud model.

## Related

- `agents-claude`, `agents-codex`, `agents-aider`, `agents-opencode` - sibling harnesses. `models-qwen` - capability axis.

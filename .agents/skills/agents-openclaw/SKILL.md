---
name: agents-openclaw
description: Harness profile for OpenClaw, an always-on multi-channel local-agent assistant with a TUI coding loop, floating over local Ollama models. Triggers - openclaw, clawhub.
---

# agents-openclaw

The **OpenClaw** harness (they/them). An always-on multi-channel assistant: the messaging dashboard (Control UI) is its center of gravity, with `openclaw tui` as the Crush/opencode-shaped terminal coding loop. Floats over local Ollama quants, so the active model is the ceiling, not "OpenClaw".

## Posture

- **Reach for it when** you want an always-on local agent across channels, or the TUI for heads-down coding. For a stronger loop, drive it under a Claude Code or Codex runtime.
- Coding profile (`tools.profile: "coding"`) gives exec / apply-patch / edit / write.

## Related

- `agents-opencode`, `agents-aider`, `agents-goose` - siblings. `models-qwen-coder` - capability axis.
- Live config + testbed live in `coilyco-bridge/agentic-os-hardware`.

# Agent compatibility check

`ward exec agent-compat` runs the daily smoke check across Claude, Codex, Goose, Aider, OpenCode, and Qwen. It is a Python `unittest` runner, so the output uses native `ok` / `FAIL` / `ERROR` / skip reporting and the process exits non-zero on failure.

## Usage

```
ward exec agent-compat
ward exec agent-compat -- --harness codex
ward exec agent-compat -- --harness codex --harness qwen
```

## Coverage

The check is intentionally cheap and non-mutating:

- **Claude, Codex, OpenCode** - CLI version probe plus agent-compose load-point drift.
- **Goose** - CLI version probe plus configured model presence.
- **Aider** - CLI version probe.
- **Qwen** - Ollama CLI probe plus Qwen model inventory reachability, using the ambient environment or Goose's configured Ollama route.

Scheduling belongs to the rollout layer. This repo owns the check definition.

## Related

- [test-harness](test-harness.md) - per-agent probe docs and findings convention.
- [harness-selection](harness-selection.md) - picking a harness and model tier.
- [FEATURES](FEATURES.md) - feature inventory.

# Agent compatibility check

`ward exec agent-compat` runs the daily smoke check across the harnesses in
ward's embedded fleet roster (Claude, Codex, OpenCode, Goose). It is a Python
`unittest` runner, so the output uses native `ok` / `FAIL` / `ERROR` / skip
reporting and the process exits non-zero on failure.

## The roster is ward's, not ours

aos is the **consumer** of the roster, never its author. The set of harnesses -
which agents exist and what they are named - is read live from
`ward agents list --json`, ward's stable embedded-fleet read surface (ward#417).
`scripts/agent-compat.py` ships only the per-harness probe *logic* (how to
smoke-test each), keyed by ward's agent name. A test
(`tests/test_agent_compat.py::test_roster_matches_ward_embedded_roster`) pins the
probe key set to `ward agents list --json`, so if ward adds, removes, or renames
an agent the check fails until aos conforms. That kills the aos<->ward roster
drift at its source (aos#310 issue 5, the leak aos#308 flagged), including the
retired `aider` / `qwen` shadow entries - `aider` is not in the fleet, and post
ward#412 `qwen` is only opencode's backing model, so its ollama inventory probe
now rides the canonical `opencode` harness.

When the ward binary is absent or predates `agents list --json`, the runner falls
back to its built-in probe set (warning to stderr) and the drift-pin test skips,
so an old host still runs the check without a hard failure.

## Usage

```
ward exec agent-compat
ward exec agent-compat -- --harness codex
ward exec agent-compat -- --harness codex --harness opencode
```

With no `--harness`, the default set is ward's live roster filtered to the probes
aos ships; `--harness` narrows to a named subset.

## Coverage

The check is intentionally cheap and non-mutating:

- **Claude, Codex, OpenCode** - CLI version probe plus agent-compose load-point drift.
- **OpenCode** - also probes ollama reachability and its qwen backing-model inventory, using the ambient environment or Goose's configured ollama route.
- **Goose** - CLI version probe plus configured model presence.

Scheduling belongs to the rollout layer. This repo owns the check definition.

## Related

- [test-harness](test-harness.md) - per-agent probe docs and findings convention.
- [harness-selection](harness-selection.md) - picking a harness and model tier.
- [FEATURES](FEATURES.md) - feature inventory.

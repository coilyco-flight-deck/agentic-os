# Context-budget report

`check-context-budget` reports the eager startup context each agent harness
loads at session start, per harness, against a per-harness token budget, with
per-source attribution. It is an on-demand tool (the `ward context-budget`
verb), not a pre-commit hook, so it carries no weight in the universal commit
path and is free to grow heavier measurement later.

## What it measures

Where the `agent-compose-size` hook caps the `AGENTS.COMPOSE.md` **sources** at
commit time, this measures the **composed output** a harness actually loads. It
reuses the composer's own resolution (gather sources, scope-filter,
harness-slice, apply overrides, compose), so the measured bytes are exactly what
each load point holds (the drift hook guarantees the on-disk file matches). For
each harness it prints the total against its budget, a fill bar, an `OVER by N`
flag when over, and the per-source token breakdown ranked biggest-first.

When no `agent-compose.yaml` is present (agent-compose is opt-in), it falls back
to measuring the installed load-point files directly, without attribution.

## Why per-harness budgets differ

The budgets are not one number. They encode three distinct failure modes:

- **claude** - attention dilution. Its composed slice alone gets the private
  overlay, so it is the heaviest, and a bloated baseline crowds the task and
  makes the model miss the obvious. The budget is a forcing function: doc growth
  is zero-sum against it.
- **codex** - its eager MCP surface is ~0. mcporter is lazy for codex (it shells
  `mcporter call` / `list` on demand and never loads tool schemas eagerly), so
  the budget only bounds the composed doc. Sweep blow-out is runtime
  accumulation a static report cannot govern.
- **opencode** - a small local qwen model, curated hardest, so its budget is
  tightest.

## Token counting

v1 uses a deterministic chars/4 proxy. tiktoken ships no qwen encoding and the
qwen BPE needs its vocab assets, so v1 stays hermetic behind a single
`count_tokens` function. The proxy is ~10% off in absolute terms but consistent
across harnesses, which is what a zero-sum budget comparison needs. Swapping in a
real qwen tokenizer is a one-function change.

## Budgets and flags

Budgets are global (this is a host-wide, not repo-scoped, tool): module defaults,
overridable by a `budgets:` mapping in `agent-compose.yaml` or by
`--<harness>-budget` flags. `--check` exits non-zero when any harness is over
budget, for CI use. `--mcporter` points at the merged mcporter config to read
codex's exposed server inventory (reported as context, since those schemas are
lazy).

## See also

- [features-agents-sessions.md](features-agents-sessions.md) - agent-compose, the composer this measures.
- [.ward/ward.yaml](../.ward/ward.yaml) - allowlisted commands.

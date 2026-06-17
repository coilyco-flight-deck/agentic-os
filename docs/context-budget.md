# Context-budget report

`check-context-budget` reports the eager startup context each agent harness
loads at session start, per harness, against a per-harness token budget, with
per-source attribution. It is an on-demand tool (the `ward context-budget`
verb), not a pre-commit hook, so it carries no weight in the universal commit
path and is free to grow heavier measurement later.

## What it measures

It sums everything a harness ingests at session start across three axes, each
with a different growth lever, then reports the total against a per-harness
budget with a fill bar and an `OVER by N` flag:

- **doc** - the composed AGENTS.md/CLAUDE.md load point. It reuses the composer's
  own resolution (gather sources, scope-filter, harness-slice, apply overrides,
  compose), so the bytes are exactly what the load point holds (the drift hook
  guarantees the on-disk file matches), with a per-source breakdown. Lever: edit
  the AGENTS.md sources. The `agent-compose-size` hook caps these sources at
  commit time; this measures the composed result.
- **skills** - every mounted skill's SKILL.md **frontmatter** (name +
  description) is eager so the model knows the skill exists; bodies load lazily
  on invoke. With a large skill surface this is routinely the **biggest** axis,
  larger than the composed doc. Lever: prune the skill set.
- **mcp** - native MCP tool schemas. Lazy through mcporter (codex shells
  `mcporter call` / `list` on demand) and deferred under ToolSearch, so the eager
  figure is ~0; reported as a server-count note, not a token sum, until a
  non-lazy path needs measuring.

When no `agent-compose.yaml` is present (agent-compose is opt-in), the doc axis
falls back to measuring the installed load-point files directly.

### Skill scope is cwd-dependent

`mount-skills.sh` empties `~/.claude/skills` and symlinks each skill dir into
per-repo `.claude/skills`, so the eager set is the global plugin skills plus the
scoped skills discoverable from the cwd. Relative skill roots are expanded
against the cwd and every workspace repo and deduped by resolved path, so the one
canonical set mounted into many repos counts once. The reported total is thus the
**workspace union** (elevated-cwd worst case); a session in one repo sees fewer.
Roots default per `DEFAULT_SKILL_ROOTS`, overridable via `skill_roots:` in
`agent-compose.yaml`.

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
`count_tokens` function. The proxy is ~10% off absolute but consistent across
harnesses, which is what a zero-sum comparison needs. The swap is one function.

## Budgets and flags

Budgets are global (host-wide, not repo-scoped): module defaults, overridable by
a `budgets:` mapping in `agent-compose.yaml` or `--<harness>-budget` flags.
`--check` exits non-zero when any harness is over budget, for CI. `--mcporter`
points at the merged mcporter config for codex's exposed server inventory.

## See also

- [features-agents-sessions.md](features-agents-sessions.md) - agent-compose, the composer this measures.
- [.ward/ward.yaml](../.ward/ward.yaml) - allowlisted commands.

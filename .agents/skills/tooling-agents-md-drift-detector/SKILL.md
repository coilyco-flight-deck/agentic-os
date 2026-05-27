---
name: tooling-agents-md-drift-detector
description: Cross-repo AGENTS.md drift detector. Surfaces forks (repos that re-state canonical content) rather than expected layering across the configured repo set.
---

# agents-md-drift-detector

## Triggers

agents drift, AGENTS.md drift, agents md drift, agents-md-drift-detector, agents drift detector, cross-repo agents check, agents sync check, agents lint, repo agents audit.

## Why

Many AGENTS.md files can exist across a repo set. Most are slim
per-repo files that delegate to canonical AGENTS.md via a
header (`See ../AGENTS.md ...` or `load globally via your client's CLAUDE.md
-> <canonical>/AGENTS.md`). That is the intended layering pattern, not
drift.

The failure mode this skill catches is the opposite: a repo's
AGENTS.md that re-states canonical content (forking) instead of
delegating. Forked copies silently mask edits to canonical and break
agents that read whatever file is in front of them.

## Procedure

```sh
coily exec agents-md-drift
```

The report goes to the vault inbox when reachable, otherwise stdout.
Override with `AGENTS_DRIFT_INBOX=<dir>` env var before invoking.

Under the hood: `make agents-md-drift` runs
`python3 .agents/skills/tooling-agents-md-drift-detector/detect.py $(ARGS)`.

Each repo's AGENTS.md is classified as one of:

- **`linked-canonical`** - symlink to canonical. No drift possible.
- **`linked-other`** - symlink to a non-canonical target.
- **`delegating`** - regular file with an explicit delegation header
  pointing at canonical. The intended layering pattern.
- **`standalone`** - regular file with no delegation header, no
  overlap with canonical section headers. Project-only AGENTS.md.
  Not drift.
- **`forked`** - regular file with no delegation header AND re-states
  canonical section headers (e.g. `## Voice Rules`, `## Git Workflow`).
  This is the failure mode.
- **`missing`** - no AGENTS.md.

The script exits non-zero if any `forked` entries exist (CI-friendly).

## Output path

Resolution order:

1. `--out <dir>` argument.
2. `AGENTS_DRIFT_INBOX` env var.
3. Configured inbox directory (env var)
   if it exists.
4. Stdout (when no inbox is reachable).

Filename is `YYYY-MM-DD-agents-md-drift.md` grouped by status.

## Notes

- The report includes every repo by name, including private ones.
  Default output goes to the configured inbox rather than the personal-OS repo for that
  reason. Override with `--out` if you want a local copy.
- Delegation-header heuristic: matches `See ../AGENTS.md`, `load
  globally via ... <canonical>/AGENTS.md`, or `<client>/CLAUDE.md ->
  <canonical>/AGENTS.md` in the first 800 chars.
- Standalone vs forked distinction: a fully standalone AGENTS.md
  (e.g. a project with genuinely different operating rules) is fine.
  A file with the same `## Voice Rules` or `## Git Workflow` sections
  as canonical, but no delegation header, has forked those sections
  and will silently drift.

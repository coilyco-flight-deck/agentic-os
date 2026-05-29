---
name: tooling-skill-authoring
description: Author, modify, and validate Claude Code skills. Covers naming, description caps, why-encoding, flat layout, Python helpers.
---

# Skill authoring

## Handbook

Structural rules (categories, frontmatter, status lines, required sections, validators, templates) live in [`references/handbook.md`](references/handbook.md). Authoring walkthrough in [`references/authoring-walkthrough.md`](references/authoring-walkthrough.md). Templates per category in [`templates/`](templates/).

The rest of this file carries opinionated authoring discipline the handbook doesn't cover: why-encoding, flat-not-nested layout, Python-helpers bias, plugin marketplace fast-forward.

## Location

**Default: skills live at `<personal-os-repo>/.agents/skills/`.** Canonical source for the cross-repo / runbook / operating-context skill surface. Global-scope copy at `~/.claude/skills/<name>` is a symlink managed by `./setup.sh`.

**Exception: per-repo co-location for pure design-reference skills.** A repo may host its own `.agents/skills/` if the skills are pure design or usage reference for *that repo only* and never get invoked under cross-repo failure conditions. Per-repo skills surface only when Claude Code is operating in that repo's directory, which is the correct scope for design references. Runbooks, investigation playbooks, and anything that fires under partial-failure stay central (see "Investigation skills live centrally").

When co-locating, the host repo must:

1. Receive the skill-discipline pre-commit hooks (`validate-skills`, `dead-cross-links`) plus the rest of the catalog suite via `make apply-agentic-os-hooks` from `agentic-os-kai`. That rollout inserts one managed `repo: https://github.com/coilysiren/agentic-os` block into the host's `.pre-commit-config.yaml`. No stamped local copies. The validators live in the `agentic_os` Python package; pre-commit pip-installs them. See [coilysiren/agentic-os#61](https://github.com/coilysiren/agentic-os/issues/61).
2. Ship a slim `.agents/skills/categories.yaml` at the skills root with only the categories the repo actually uses. The validator reads this path directly.
3. Run `pre-commit install` in the host repo. That activates the hooks for every commit.

No `setup.sh` is required in the host repo. Claude Code auto-discovers skills under any `.agents/skills/` in the working tree.

## Authoring

Directory under `.agents/skills/` with `SKILL.md` (frontmatter: `name`, `description` + instructions). Commit in the personal-OS repo, rerun `./setup.sh` from repo root (idempotent symlink refresh).

Bootstrap also handles client CLAUDE.md import, workspace CLAUDE.md import, parent-dir AGENTS.md symlink. Uses `ln -s`; on Windows needs `MSYS=winsymlinks:nativestrict` + Developer Mode.

Run the validator before committing for fast feedback:

```sh
pre-commit run skill-conventions --all-files
pre-commit run dead-cross-links --all-files
pre-commit run em-dash-check --all-files
```

The structural validator enforces the category taxonomy from `.agents/skills/categories.yaml`. If your skill name doesn't match an allowed prefix or exact-name, the validator rejects it. See the handbook for the prefix list.

## Encode the why, not just the what

Skills exist because every agent session starts from zero. There is no Sarah to ask why a rule was written, so undocumented reasoning gets re-derived badly on each fresh context, or the rule gets deleted by an agent who cannot see why it mattered. Each rule below captures decision reasoning, not just procedure. Hold that line for new sections.

Shape: lead with the rule, then a **Why:** line (incident, constraint, prior failure mode that produced it), then a **How to apply:** line (when the rule fires). Date-stamp the flag where useful (e.g. "Flagged 2026-04-26") so a future read can judge whether the why is still load-bearing.

Framing reference: https://simme.dev/posts/the-end-of-just-ask-sarah/.

## Skills are flat, not nested

Every skill is a peer directory directly under `.agents/skills/`. Do **not** nest sub-skills inside another skill's directory (e.g. `meta-skill/sub-skill/SKILL.md`). Nested-skill discovery is poorly supported by the harness, and `setup.sh` only symlinks top-level skill dirs to `~/.claude/skills/<name>`. Anything below the top level is invisible to the loader.

When a meta-skill needs to route to other skills, the routed skills live as **flat peers** alongside it. The meta's job is to name them and describe when each fires; the loader handles each one independently.

**Why:** caught early while building a meta-skill router. Initial design assumed sub-dir nesting per a team-coordination plugin pattern. That pattern relied on team-coordination plumbing (separate plugin repo, `commands/` symlinks, etc.) that doesn't apply in a single-operator personal-OS repo. Flat is the only shape the existing setup actually supports.

**How to apply:** when authoring a meta-skill, the routing table lists peer-skill names, not paths into the meta's own dir. New routed skills get their own top-level directory. If you find yourself wanting to nest, that's a signal the meta should instead be a thin SKILL.md that describes shared discipline, with the actual work split across peer skills.

## Extended discipline

Three longer-form rules live in [`references/discipline.md`](references/discipline.md): investigation/runbook skills live centrally (not co-located with the tool they investigate), plugin-marketplace fast-forward, and full documentation discipline (layout, size caps, code comments).

## Bias toward Python helpers, not pure-prompt skills

When a skill parses files, walks directories, queries SQLite, or does any structured data manipulation, write a Python script in the skill directory and have SKILL.md call it. Pure prompt instructions are fine for narrative steps; Python is right for anything where determinism, speed, or testability matter.

Helpers go in the skill dir alongside SKILL.md, get committed to the personal-OS repo, run with the system `python3` (stdlib-first; reach for trafilatura, lxml, etc. only when stdlib genuinely doesn't suffice).

Flagged 2026-04-26.

**Why:** procedure-as-prompt loses fidelity each time the LLM re-derives boilerplate (date math, path globbing, file IO). Committed Python is auditable, fast, and the same on every host. The LLM tier should focus on synthesis, not parsing.

**How to apply:** new skill that ingests data → start with `script.py` (or named subcommands), have SKILL.md document inputs/outputs/invocation. Existing skill that's been doing parsing in-prompt → migrate to Python on next touch.

## Frontmatter aliases

Lead with the canonical name plus 2-3 natural-language phrasings a user might reach for. **500-byte hard ceiling on the whole `description:` field.** If a skill needs more trigger surface than that, the fix is a better name, a router parent (see `coily-meta`, `ops-social-gws-gmail`, `kai-execution-mode` for the pattern), or splitting the skill. Not a longer description.

**Router-parent carve-out:** a router skill claiming a broad domain keyword surface (so child skills can stay terse) may exceed 500 bytes when the extra surface is doing real routing work, not alias-packing. The router shape has to be load-bearing - "router with two children" does not qualify. The Gmail and Google Calendar parents both do, today.

**Why:** the `description` field is eager-loaded into every Claude turn forever. Aliases are paid only per invocation. At ~100 skills, the eager surface already crowds the catalog, and the system-reminder skill catalog truncates past ~80 entries, so selection accuracy degrades from sheer surface size before token cost even enters the picture. Alias-packing is the most expensive possible layer to solve discoverability at. Filed as [agentic-os-kai#583](https://github.com/coilysiren/agentic-os-kai/issues/583); the cap dropped from 600 to 500 after the post-#583 sweep (only 3 outliers remained over 500, all trimmable).

**How to apply:** when authoring a new skill, write `description:` as one sentence of purpose plus 2-3 phrasings. When tempted to add a fourth alias, rename the skill or hoist a router parent instead. LUCA-driven cold-skill pruning (future audit chain) will validate whether existing aliases earn their bytes.

## Triggers

skill, SKILL.md, frontmatter, plugin, .agents/skills, authoring skill, validator, categories.yaml, skill location, naming, category prefix, description size, flat layout, Python helpers, plugin marketplace, documentation discipline, doc layout, code comments.

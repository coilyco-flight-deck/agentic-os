---
name: tooling-skill-authoring
description: Author, modify, and validate agent skills. Covers naming, description caps, why-encoding, flat layout, Python helpers.
---

# Skill authoring

## Handbook

Structural rules (categories, frontmatter, status lines, required sections, validators, templates) live in [`references/handbook.md`](references/handbook.md), now a slim index over topical files. Authoring walkthrough in [`references/authoring-walkthrough.md`](references/authoring-walkthrough.md). Templates per category in [`templates/`](templates/).

The rest of this file carries opinionated authoring discipline the handbook doesn't cover: why-encoding, flat-not-nested layout, Python-helpers bias, frontmatter aliases.

## Location

**Default: ordinary skills live at `<provider-repo>/.agents/skills/`.**
These use `SKILL.md` and form the harness-discoverable surface.

**Role-scoped source: `<provider-repo>/.agents/composed/`.** These use
`COMPOSED.md` and are bound in `.agents/roles.kdl`. Agent-compose promotes only
the selected role's sources to `SKILL.md`. Never place `SKILL.md` anywhere
under `.agents/composed/`.

**Exception: per-repo co-location for pure design-reference skills.** A repo may host its own `.agents/skills/` if the skills are pure design or usage reference for *that repo only* and never get invoked under cross-repo failure conditions. Per-repo skills surface only when the harness is operating in that repo's directory, the correct scope for design references. Runbooks, investigation playbooks, and anything that fires under partial-failure stay central. Co-location requirements (catalog hooks via `make apply-agentic-os-hooks`, a slim `categories.yaml`, `pre-commit install`) live in [`references/co-location.md`](references/co-location.md).

## Authoring

Create an ordinary source with `SKILL.md`, or a role-scoped source with
`COMPOSED.md`. Both use the same `name` and `description` frontmatter. Bind
each role-scoped source in `.agents/roles.kdl`.

Run the validator before committing for fast feedback:

```sh
pre-commit run skill-conventions --all-files
pre-commit run dead-cross-links --all-files
pre-commit run em-dash-check --all-files
```

The structural validators enforce the category taxonomy from
`.agents/skills/categories.yaml`. `check-skills` covers ordinary sources.
`check-composed-skills` covers role-scoped sources and their isolation.

## Opinionated discipline

Four high-signal rules each carry decision reasoning in [`references/opinionated-discipline.md`](references/opinionated-discipline.md):

- **Encode the why, not just the what** - lead with the rule, then **Why:**, then **How to apply:**. Every fresh agent context re-derives undocumented reasoning badly.
- **Sources are flat, not nested** - every source is a peer directory under `.agents/skills/` or `.agents/composed/`.
- **Bias toward Python helpers, not pure-prompt skills** - parsing, globbing, SQLite, date math go in committed `python3`. The LLM tier does synthesis, not parsing.

Frontmatter-alias discipline (validator-enforced description ceiling - `categories.yaml:max_description_bytes`, default 500, kai-parity target 200 - and the router-parent carve-out) lives in [`references/frontmatter-aliases.md`](references/frontmatter-aliases.md).

## Extended discipline

Three longer-form rules live in [`references/discipline.md`](references/discipline.md): investigation/runbook skills live centrally (not co-located with the tool they investigate), plugin-marketplace fast-forward, and full documentation discipline (layout, size caps, code comments).

## Triggers

skill, SKILL.md, COMPOSED.md, composed skill, role-scoped skill, roles.kdl,
frontmatter, plugin, .agents/skills, .agents/composed, authoring skill,
validator, categories.yaml, skill location, naming, category prefix,
description size, flat layout, Python helpers, documentation discipline.

# Skills Repository Handbook

**Purpose.** This file is the single source of truth for everything uniform and structured about `<personal-os-repo>/.agents/skills/`. Read it cold and you should be able to recreate the repo's skill organization from scratch: the category taxonomy, the canonical SKILL.md shape per category, the validator, the templates, the pre-commit wiring, the cross-link rules, and the rules for adding a new category.

This file is paired with [`categories.yaml`](../../categories.yaml) (at `.agents/skills/categories.yaml`), the machine-readable spec consumed by the `coilysiren/agentic-os` skill-discipline validator. When the two disagree, the YAML is authoritative for the validator and this file should be updated to match.

## 1. Layout

```
<personal-os-repo>/
├── .agents/skills/
│   ├── <personal-prefix>-<topic>/                            # operating-context rules
│   ├── daily-<topic>/                          # cron'd inbox routines
│   ├── ops-social-gws-<verb>/                  # Gmail family
│   ├── ops-social-google-<topic>/              # Calendar family
│   ├── ops-eng-sentry-<topic>/                 # Sentry review playbooks
│   ├── ops-investigation-<topic>/              # per-topic investigation guides
│   ├── ops-investigation/                      # investigation router
│   ├── <ops-investigation-meta>/              # meta-discipline router
│   ├── gaming-eco-<topic>/                     # Eco modding
│   ├── gaming-steam/                           # Steam library
│   ├── gaming-factorio/                        # placeholder
│   ├── writing-<topic>/                        # prose / voice / issue authoring
│   ├── home-<system>/                          # smart-home control
│   ├── tooling-<topic>/                        # agent-ecosystem meta
│   ├── vault-<topic>/                          # Obsidian vault tooling
│   ├── categories.yaml                         # machine-readable spec (root)
│   └── skill-creator/                          # this skill (handbook + templates)
│       ├── SKILL.md                            # entrypoint, points at this handbook
│       ├── references/
│       │   ├── handbook.md                     # YOU ARE HERE
│       │   └── authoring-walkthrough.md        # how to draft a skill
│       └── templates/                          # one template per shaped category
├── scripts/
│   ├── check-em-dashes.py                      # local voice-rule hook
│   └── leak-check.py                           # local private-string denylist
└── .pre-commit-config.yaml                     # subscribes to coilysiren/agentic-os hooks + local hooks
```

**No skills outside `.agents/skills/`.** No skills inside other skills' directories. Flat is the only shape the loader supports.

## 2. Categories

Eleven prefix families and five exact-name skills. Pick the prefix up front; the validator rejects unknown prefixes.

* `<personal>-*` (e.g. `kai-*`) - operating context - durable rules about how the user works (preferences, voice, git workflow, repo registry pointers).
* `daily-*` - cron'd inbox routines - fetch / digest / render shape, write to vault inbox.
* `ops-social-gws-*` - Gmail family - verb-shaped children plus an `ops-social-gws-shared` parent.
* `ops-social-google-*` - Calendar family.
* `ops-eng-sentry-*` - Sentry review playbooks.
* `ops-investigation-*` - investigation playbooks and runbooks. Status-enforced. Required H2 sections enforced.
* `gaming-eco-*` - Eco modding (investigation, scaffolding, source-auditing).
* `writing-*` - prose / voice / issue authoring surface (writing-voice-guide-linter, writing-bluesky, writing-refactor-plan, writing-to-issues).
* `home-*` - smart-home control at My House (hue, sonos, cast).
* `tooling-*` - agent-ecosystem meta (tooling-skillsmp, tooling-capability-scout, tooling-mcp-servers, tooling-supply-chain-audit, tooling-agents-md-drift-detector, tooling-security-boundary-discipline). `meta-tooling skills may stay in the personal-prefix` since they encode operating-context discipline.
* `vault-*` - Obsidian vault tooling (cli, markdown rules, vault rules).
* `coding-*` - code-engineering recipes (Discord bot scaffolding, Terraform module library, GitHub PR workflow). Reusable build patterns, not tooling on the agent ecosystem itself.

Exact-name skills (don't fit a prefix):

* `ops-investigation` - router across all `ops-investigation-*` skills.
* `<ops-investigation-meta>` - meta-discipline router (cross-cutting investigation rules).
* `skill-creator` - this skill (handbook + authoring loop).
* `gaming-steam` - Steam library (one-off).
* `gaming-factorio` - placeholder for future Factorio work.
* `coily-passthroughs` - symlink into `coily's skills dir`. Single source of truth lives in the coily repo; this name is registered as an exact-name skill in the personal-OS repo so the validator recognizes it without owning its content. Symlinks are skipped from validation but their names are recognized for cross-link resolution.

Picking a category for a new skill:

* A new investigation playbook for a user-system component goes to `ops-investigation-*`.
* An Eco-game-server failure investigation goes to `gaming-eco-investigation`. The `ops-investigation` router cross-links it.
* A new shape that doesn't fit any of the above: **stop and update this handbook + `categories.yaml` first**, then create the skill. The validator rejects unknown prefixes by design.

## 3. SKILL.md frontmatter (universal)

Every SKILL.md begins with YAML frontmatter:

```markdown
---
name: <directory-name>
description: Use when <routing condition>. Include the canonical task shape plus a compact alias set. Keep discovery text short; put procedure in the body.
---
```

Rules:

* `name` MUST equal the directory name. Validator enforces this.
* `description` MUST be non-empty. Validator enforces this.
* `description` is routing metadata, not documentation. Claude and Codex both see it before reading the skill body. The field answers "when should the agent open this skill?"
* `description` may include a compact `Triggers - foo, bar, baz` tail when trigger aliases help. The tail is optional, and it should earn its bytes. Avoid exhaustive keyword bags.
* Cross-links to other skills use either:
  * bare backticks `` `skill-name` `` for in-prose passing mentions, or
  * markdown link `` [`skill-name`](../skill-name/SKILL.md) `` for navigable references.
  Either form is fine; both are validated. The dead-link checker resolves the markdown target.

### Description budgets

Descriptions are the highest-cost text in the skill system because every candidate skill pays the cost before an agent decides what to open. Claude's larger context can tolerate chatty descriptions, but Codex routing benefits from shorter, sharper metadata. Optimize the eager surface first; leave the skill body rich.

Hard validator limits:

* **Normal skills** - 500 by default. Override to 200 for a Codex-optimized catalog.
* **Router/meta skills** - 2x the cap when the matched category declares `role: router` or `role: meta`. At the default cap, that means 1000 bytes.
* **SKILL.md bodies** - 500 lines and 10 KB. Past either, the loader degrades. Move detail into `references/`, `scripts/`, or `assets/`.

Target bands:

* **Pointer skills** - under 160 chars. Use this when the body mostly points at a canonical doc elsewhere.
* **Normal task skills** - 120-200 chars. Most coding, writing, gaming, vault, and tool-usage skills should fit here.
* **Complex task skills** - 220-300 chars. Use this for skills with several adjacent trigger phrasings or one important boundary.
* **Router/meta skills** - 250-400 chars. A router earns extra surface only when it prevents many child skills from carrying broad aliases.
* **Rare exceptions** - 400-500 chars for public-safety, MCP routing, or cross-repo failure handling where false negatives are expensive.
* **Cleanup signal** - over 500 chars means fix the description or explicitly justify a router/meta role in `categories.yaml`.

What belongs in `description`:

* The main user intent or task shape.
* A few concrete trigger phrases Kai actually says.
* Critical disambiguators that prevent the wrong skill from opening.
* Router fan-out surface, only for true router skills.

What belongs in the body instead:

* Procedure, command sequences, examples, checklists, policy rationale, historical incidents, implementation details, path inventories, long voice-mangle lists, and "why this exists" context.

Alias discipline:

* Lead with the canonical noun phrase, then 3-8 high-signal aliases.
* Stop adding aliases when the next one is just a spelling variant, a synonym the model already knows, or a phrase Kai rarely says.
* For voice dictation mangles, keep the common mangles in the description and move rare mangles into the body.
* If a skill needs more than 8-12 aliases, rename the skill, add a router parent, or split the domain.

Templates:

```yaml
description: Use when Kai asks to <verb> <domain>, especially <2-4 concrete trigger phrases>.
```

```yaml
description: Router for <domain> skills. Use when Kai asks about <broad domain>, then open the child skill for the specific verb or system.
```

```yaml
description: Pointer for <rule/domain>. Use when Kai asks about <trigger>; read <canonical file> for the full procedure.
```

Audit baseline from a 2026-05-21 Codex scan of 103 local skills:

* Average description length was 384 chars.
* 96 descriptions were over 240 chars.
* 66 descriptions were over 360 chars.
* 4 descriptions were over 500 chars.

That baseline is workable for Claude, but it is too chatty for a Codex-optimized lazy-loading surface. When touching a skill, shorten the description before expanding the body.

## 4. The status line (under H1, where enforced)

Status enforcement is per-category. See `categories.yaml` for which categories enforce it. The format when enforced:

```markdown
# <Title>

Status: <emoji> <Kind> | Last <updated|tested>: YYYY-MM-DD
```

The emoji is part of the canonical format and pairs one-to-one with the kind. Validator rejects any other pairing.

Currently enforced:

* `ops-investigation-*` - kinds: `🟢 Active`, `⚪ Stub`, `🛠 Runbook`, `📋 CaseStudy`. Freshness: `Last updated`.
* `ops-investigation` (router) - kind: `🗺 Router`. Freshness: `Last updated`.

Status-kind sub-shapes for `ops-investigation-*`:

* **Active.** The default. Real, live investigation guide. Required H2 sections enforced.
* **Stub.** Placeholder, will be expanded. Only `Overview` required; that section explains why it's a stub and where the work will land.
* **Runbook.** Operational rollout/runbook. Free-form body beyond `Overview`.
* **CaseStudy.** Single-incident worked example. Free-form beyond `Overview`. Cross-link the underlying pattern.

Categories without status enforcement: free-form. Add a status line voluntarily if it pulls weight (e.g., a daily-* skill noting when its data sources last changed shape), but the validator does not require it.

## 5. Required H2 sections per category

Validator-enforced where listed. Names are exact (case-insensitive, leading/trailing whitespace ignored). Order is recommended but not enforced. Categories not listed below are free-form.

### `ops-investigation-*` (Status: Active)

H1 must match `^# .+ Investigation Guide$` for `Active` and `Stub`. `Runbook` and `CaseStudy` H1s are free-form.

```markdown
## Overview
## Data sources
## Investigation procedure
## Common patterns
## Common dead ends
```

Notes:

* `Overview` answers "what is this thing?" in 1-3 paragraphs.
* `Data sources` lists the systems / collections / APIs / log streams you'll be reading.
* `Investigation procedure` is the step-by-step.
* `Common patterns` covers recurring failure modes / known categories.
* `Common dead ends` is what NOT to do, with reasons.

Optional sections (allowed, not required): `Architecture`, `Rollout phases`, `Monitoring runbook`, etc.

### Routers (`ops-investigation`)

```markdown
## Routing table
```

Plus any cross-cutting rules that apply to every routed-to skill. The router is NOT the place for procedure that's specific to one routed-to skill.

### All other categories

Free-form. Frontmatter still enforced.

### Repo AGENTS.md heading set

The catalog-trifecta validator enforces a standard H2 set for every repo-local `AGENTS.md`:

* `## Scope`
* `## Project shape`
* `## Repo boundaries`
* `## Commands`
* `## Validation`
* `## Safety`
* `## Cross-repo contracts`
* `## Release`
* `## Agent rules`
* `## See also`

These headings are intentionally broad. If a repo has nothing special for a section, keep the heading and write one line saying the repo inherits the workspace default or has no repo-local rule. The point is fast agent scanning, not forcing every repo to invent policy.

## 6. Validators

The structural validator and dead-link checker ship from [`coilysiren/agentic-os`](https://github.com/coilysiren/agentic-os) and are consumed via pre-commit. The em-dash check is a small local hook because the upstream is voice-neutral by design.

### Documentation-wide validators

`catalog-trifecta`, `catalog-doc-size`, `documentation-layout`, and `code-comments` apply beyond skills. Together they enforce the doc surface shape:

* `README.md`, `AGENTS.md`, and `docs/FEATURES.md` exist, cross-link, and stay under 80 lines / 4000 chars.
* `AGENTS.md` uses the standard repo-local H2 set.
* Markdown lives only at repo root, flat `docs/*.md`, or skill folders, and every Markdown file stays under 80 lines / 4000 chars.
* Code comments are one standalone line, max 90 chars, with long explanation moved to docs.

### `skill-conventions` (upstream) - structural check

Reads `.agents/skills/categories.yaml`, walks `.agents/skills/`, applies all checks, exits non-zero with a per-violation report.

What it checks:

1. **Skill prefix.** Every directory under `.agents/skills/` matches an allowed prefix or exact name.
2. **SKILL.md exists.**
3. **Frontmatter valid.** Has `name` (equal to dir name) and non-empty `description`.
4. **Description prefix** (when enforced per category). Optional. Most categories leave this off.
5. **Forbidden directory names** (per category, when set).
6. **Forbidden body strings** (global allow-list).
7. **Status line** (when enforced). Format `Status: <emoji> <Kind> | Last <updated|tested>: YYYY-MM-DD`. Kind in allowed list, emoji matches the kind's required pairing.
8. **H1 pattern** (when enforced).
9. **Required H2 sections** (when enforced). Dispatched by Status kind.
10. **Section lead lines** (when enforced).
11. **Stale skill-name backtick references.** Catches `` `<prefix>-<topic>` `` references whose target skill doesn't exist.
12. **SKILL.md size caps.** 500 lines, 10 KB. Past either, the loader degrades. Push detail into a sibling `references/` file.
13. **Symlinks under `.agents/skills/`.** Symlink dirs are skipped, not validated. The loader follows them; the validator walks the canonical target.

### `dead-cross-links` (upstream) - cross-link check

Walks every Markdown file under `.agents/skills/`, extracts inline `[text](target)` links, fails on any local-relative target that doesn't resolve.

What it skips intentionally:

* External URLs (`http://`, `https://`, `mailto:`, etc).
* Paths escaping the repo via `../` (treated as external).
* Anchors (`#section`) and placeholder targets (`...`, `TBD`, `TODO`).
* Inside fenced code blocks.
* Files named `TEMPLATE.md`.

### `em-dash-check` (local) - voice rule

`scripts/check-em-dashes.py` flags U+2014 in SKILL.md prose, masking inline code, fenced code, quoted strings, and link targets first. Stays local because the upstream validator is voice-neutral and em-dashes are a personal preference, not a general convention.

### Pre-commit wiring

`.pre-commit-config.yaml` subscribes to `coilysiren/agentic-os` at a pinned tag for `skill-conventions`, `dead-cross-links`, and `commit-closes-issue`. The four local hooks (`trufflehog`, `leak-check`, `em-dash-check`, `setup-symlinks`, plus the `coily-trailer` prepare-commit-msg hook) stay as `repo: local` entries.

Bump the `rev:` to pull upstream changes. Add new local checks as new `repo: local` hook entries.

## 7. Templates

One file per shaped category at [`../templates/`](../templates/):

* `ops-investigation.md` - investigation guide (Active)
* `ops-investigation-router.md` - router

Other categories are free-form and don't need templates.

To author a new shaped skill: copy the template, fill in. The validator catches anything you forgot.

## 8. Cross-linking rules

* Use **skill names**, not relative paths, in prose mentions. The router resolves.
* An `ops-investigation-*` skill that uses an MCP heavily cross-links to the relevant `tooling-mcp-servers` or sibling skill, and the corresponding skill cross-links back where the link pulls weight.
* The `ops-investigation` router keeps its routing table current. Adding a new `ops-investigation-*` skill = update the router in the same commit.
* `<ops-investigation-meta>` is the meta-discipline layer. It cross-links to `ops-investigation` (the router) and to specific subject skills for examples.

## 9. Rules for adding a new category

You almost never should. Most asks fit one of the eleven families. If you genuinely have a new shape:

1. Open a draft of `categories.yaml` with the new category. Pick `kind: prefix` or `kind: exact`. Decide whether to enforce status and sections.
2. Update this handbook (§2 list, plus a per-category subsection in §5 if sections are enforced).
3. Add a template under `skill-creator/templates/` if the category has a fixed shape.
4. Run the validator to make sure it now passes against the proposed addition.
5. Then create the first skill of the new category.

The validator rejects unknown prefixes by design. It forces this discussion to happen.

## 10. Voice + writing conventions

Inherited from the user's AGENTS.md. Highlights:

* No em-dashes (U+2014). Use periods, commas, parens, or ` - `.
* No italics, no semicolons in prose.
* No tables in prose. Use flat bullet lists.
* "Load-bearing" is physical-only.
* See the user's voice guide for pronoun rules.
* Match the user's intent, not literal trigger keywords. Trigger lists are examples, not exhaustive.
* Imperative voice. Explain why over MUSTs.

The validator's em-dash check flags U+2014 in SKILL.md prose. Wrap legitimate uses (e.g. quoted prose from someone else) in backticks or double quotes.

## 11. Symlinks and the global skill surface

`./setup.sh` from `<personal-os-repo>/` creates symlinks at `~/.claude/skills/<name>` pointing back at each top-level directory under `.agents/skills/`. Restart Claude Code after running setup so the loader picks up new entries.

Some skills (e.g. `coily-passthroughs`) live as symlinks inside `.agents/skills/` rather than real directories. The validator skips symlinks; the canonical target is validated where it lives.

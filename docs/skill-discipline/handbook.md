# Skill Discipline Handbook

This handbook documents the skill-discipline rules enforced by the pre-commit hooks shipped from this repo. It pairs with [`examples/categories.yaml`](../examples/categories.yaml) (the machine-readable spec) and the hooks declared in [`.pre-commit-hooks.yaml`](../../.pre-commit-hooks.yaml).

If your repo follows this handbook, the hooks will pass. If they disagree, the spec is authoritative for the validator and this file should be updated to match.

## 1. Layout

A repo using these hooks ships skills under `.agents/skills/`, the location Claude Code reads from. The layout the hooks expect:

```
<your-repo>/
├── .agents/skills/
│   ├── categories.yaml        # spec consumed by skill-conventions hook
│   ├── <skill-name>/
│   │   ├── SKILL.md           # frontmatter + body
│   │   └── references/        # optional, for content that overflows SKILL.md
│   └── <another-skill>/
│       └── SKILL.md
└── .pre-commit-config.yaml    # declares this repo's hook subscriptions
```

Every skill is a peer directory directly under `.agents/skills/`. **Skills must be flat**, never nested inside another skill. Agent harnesses do not reliably discover sub-skills, and the validator only walks top-level directories.

## 2. Categories

`categories.yaml` lists the families of skills the repo allows. Two kinds:

* **Prefix family**: every directory whose name starts with the prefix matches. Example: `coding-` matches `coding-typescript`, `coding-rust`, etc.
* **Exact-name**: a single named skill. Use for routers, meta-skills, and one-offs that do not fit a family.

The validator rejects any skill whose name does not match an allowed prefix or exact entry. This is the point. If you have a genuinely new shape:

1. Add the new prefix or exact entry to `categories.yaml`.
2. Update this handbook (or your project's version of it) so future authors know the family exists and what it is for.
3. Then create the first skill in the new family.

Do not bypass the spec by silently adding a skill with an unrecognized name.

## 3. SKILL.md frontmatter

Every SKILL.md begins with YAML frontmatter. Two fields required:

```yaml
---
name: <directory-name>
description: <one paragraph; pack keyword aliases for discoverability>
---
```

Rules (validator-enforced):

* `name` MUST equal the directory name.
* `description` MUST be non-empty.
* `description` is what an agent harness keyword-matches when deciding whether to invoke the skill. Lead with the canonical name, then pack 5-10 natural-language phrasings users (and agents) might reach for. End with a packed `Triggers - foo, bar, baz.` line.

Bias toward over-triggering. Harnesses tend to under-invoke skills.

## 4. The status line (where enforced)

Per-category. If `enforce_status: true` in the spec, every SKILL.md in that category needs a status line directly under the H1:

```markdown
# <Title>

Status: <emoji> <Kind> | Last <updated|tested>: YYYY-MM-DD
```

The emoji is part of the canonical format and pairs one-to-one with the kind. The validator rejects any other pairing. Pick kinds for your taxonomy (e.g. `Active 🟢`, `Stub ⚪`, `Runbook 🛠`, `Router 🗺`) in `categories.yaml`.

Categories without status enforcement are free-form. Add a status line voluntarily if it carries information (e.g. a digest skill noting when its data sources last changed shape), but the validator does not require one.

## 5. Required H2 sections (where enforced)

Per category and per status kind. If `required_sections.by_status` is set for a category, every SKILL.md of that status kind must contain the listed H2s. Section names match case-insensitively, leading and trailing whitespace ignored. Order is recommended but not enforced.

Use this for shaped categories where a missing section is a real problem (a runbook with no procedure, a router with no routing table). Free-form categories should leave this alone.

## 6. Voice rules (project standard, honor-system)

These are the writing conventions the rest of this handbook follows. The validator does not enforce them. Adopt them in your project's handbook if they fit; drop or replace if your project has different voice.

* **No italics.** Use bold for structural anchors at the start of bullets, or for terms of art on first mention. Italics for emphasis tends to read as performative.
* **No semicolons in prose.** Split into two sentences. Code is fine.
* **No prose tables.** Use flat bullets: `* anchor - category - detail`. Tables are correct when the structure is genuinely tabular (a machine-readable spec, a matrix of cases). They are wrong when you reach for one because the prose is getting hard to read - fix the prose instead.
* **Imperative voice in procedure.** "Run X. Check Y." beats "you should run X and then you might want to check Y."
* **Explain the why, not just the what.** Every rule should carry the reason it exists. Future readers need the why to judge edge cases. See section 9.

## 7. Size caps

Three size caps in `categories.yaml`, all with built-in defaults that apply when unset. Set any value to `0` to disable that specific check.

* `max_skill_md_lines` (default `500`) and `max_skill_md_bytes` (default `10000`) cap the SKILL.md file itself. Past either, agent harnesses degrade: the loader either refuses the file or drops it from context. Push detail into `<skill>/references/<topic>.md` files when a SKILL.md fills up. Reference files are not capped.
* `max_description_bytes` (default `500`) caps the frontmatter `description` field. Every skill's description is loaded into every agent session for keyword matching, so descriptions are pure always-on context cost. 500 fits a canonical-name + one sentence of trigger phrasings; past that you're paying for padding.
  * **Router/meta exception**: skills whose category declares `role: router` or `role: meta` get **2x** the cap (default 1000). Routers genuinely need wider keyword surface to fan out to all the skills they cross-link. The validator applies the multiplier automatically.

### Description budget targets

The validator enforces a hard byte cap, but the practical target should be lower. Treat `description` as routing metadata, not documentation. Codex and Claude both see this text before deciding whether to open the skill body.

* **Pointer skills** - under 160 chars. Use this when the body mostly points at a canonical doc elsewhere.
* **Normal task skills** - 120-200 chars. Most coding, writing, gaming, vault, and tool-usage skills should fit here.
* **Complex task skills** - 220-300 chars. Use this for skills with several adjacent trigger phrasings or one important boundary.
* **Router/meta skills** - 250-400 chars normally. A router earns extra surface only when it prevents many child skills from carrying broad aliases.
* **Rare exceptions** - 400-500 chars for public-safety, MCP routing, or cross-repo failure handling where false negatives are expensive.

Put the main task shape, a few trigger phrases, and critical disambiguators in `description`. Put procedure, examples, policy rationale, command sequences, long voice-mangle lists, implementation details, and historical context in the body or `references/`.

If a skill needs more than 8-12 aliases in the description, rename the skill, add a router parent, or split the domain.

### Frozen-archive exemption

`archive_path_components` (default `[]`) lists path components that mark a frozen archive. Any `.md` whose path contains one of these is skipped from the size caps — but only the size caps. Stale-ref, forbidden-body-string, and frontmatter checks still apply.

The motivation: investigation writeups, per-incident case libraries, and ticket-stamped diagnoses are loaded by name when an agent revisits the incident, not by the loader on trigger. Forcing splits on a 28KB rollout analysis destroys narrative for zero loader benefit. The convention this enables: park frozen content under a directory whose name is in the list (`results/`, `archive/`, etc.) and the cap stops applying.

```yaml
archive_path_components:
  - results
```

## 8. Cross-links

Two valid forms for in-prose references to other skills:

* **Bare backticks** `` `skill-name` `` for passing mentions in prose. Not navigable.
* **Markdown link** `` [`skill-name`](../skill-name/SKILL.md) `` for navigable references.

Either form: if the name does not resolve to a real skill in the repo, `check_dead_links.py` flags it.

External URLs, mailto links, bare anchors (`#section`), and paths that escape the repo via `../` are out of scope for the dead-link check.

## 9. Encode the why, not just the what

Every agent session starts cold. There is no human in the loop to ask "why was this rule written?" Undocumented reasoning gets re-derived badly, or the rule gets deleted by an agent who cannot see why it mattered.

When you write a rule, lead with the rule, then write a **Why:** line (the incident, constraint, or prior failure mode that produced it), then a **How to apply:** line (when the rule fires). Date-stamp the flag where useful so future readers can judge whether the why is still load-bearing.

Framing reference: [The end of "just ask Sarah"](https://simme.dev/posts/the-end-of-just-ask-sarah/).

## 10. The three hooks

`.pre-commit-hooks.yaml` exposes three hooks. Wire each one explicitly in your repo's `.pre-commit-config.yaml`.

### skill-conventions (pre-commit, pre-push)

Runs `validate_skills.py`. Checks frontmatter, prefix/exact match, status (where enforced), H1 pattern, required sections, forbidden body strings, stale skill-name backtick references, size caps. Symlinks under `.agents/skills/` are skipped, since their canonical target is validated where it lives.

### dead-cross-links (pre-commit, pre-push)

Runs `check_dead_links.py`. Walks every Markdown file under `.agents/skills/`, extracts inline `[text](target)` links, fails on any local-relative target that does not resolve to a real file. External URLs, anchors, placeholders (`...`, `TBD`, `TODO`), and paths escaping the repo are skipped.

### catalog-trifecta (pre-commit, pre-push)

Runs `check_catalog_trifecta.py`. Enforces the repo entrypoint set: `README.md`, `AGENTS.md`, `docs/FEATURES.md`, and one catalog YAML (`.coily/coily.yaml` or `.agent-guard/agent-guard.yaml`). Each Markdown file needs `## See also`, links to the other entrypoints, and the convention citation.

`AGENTS.md` also carries a required repo-local heading set so agents can scan operating rules without guessing each repo's prose shape:

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

### documentation-layout (pre-commit)

Runs `check_documentation_layout.py`. Enforces Markdown placement across the repo:

* root Markdown is limited to the universal allow-list (`README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE.md`);
* ordinary documentation lives in flat `docs/*.md`;
* skill documentation lives under `.agents/skills/`, `.agents/skills/`, or `skills/`;
* `docs/` has no subdirectories. Use filename prefixes when grouping is needed;
* every Markdown file stays under the size caps enforced by [`check_documentation_layout.py`](../../agentic_os/check_documentation_layout.py) (loader-bound tier for AGENTS.md / SKILL.md, standard tier for everything else).

### code-comments (pre-commit)

Runs `check_code_comments.py`. Enforces code-comment discipline for common source files: standalone comments are one line, max 90 chars, and not contiguous. Longer durable explanation belongs in `docs/*.md`; code gets a short pointer only.

### commit-closes-issue (commit-msg)

Runs `check_commit_closes_issue.py`. Reads the commit message and rejects it if no `closes #N`, `fixes #N`, or `resolves #N` keyword is present for an issue in the same repo. Cross-repo refs (`owner/other-repo#N`) are rejected. Merge / Revert / fixup! / squash! commits are exempt.

This hook is independent of skill authoring but ships in the same repo because it carries the same family of discipline: a small, automated gate that catches process drift before it lands.

# Skills Repository Handbook

**Purpose.** Single source of truth for everything uniform and structured about `<personal-os-repo>/.agents/skills/`. Read the linked sections cold and you can recreate the repo's skill organization from scratch: the category taxonomy, the canonical SKILL.md shape per category, the validator, the templates, the pre-commit wiring, the cross-link rules, and the rules for adding a new category.

This handbook is paired with [`categories.yaml`](../../categories.yaml) (at `.agents/skills/categories.yaml`), the machine-readable spec consumed by the `coilysiren/agentic-os` skill-discipline validator. When the two disagree, the YAML is authoritative for the validator and these files should be updated to match.

The handbook is split into topical references so each stays under the documentation-layout caps. Read the one you need:

* [Layout](handbook-layout.md) - §1 repo layout tree. Routes to [categories](handbook-categories.md) for §2 (the eleven prefix families, exact-name skills, how to pick a category).
* [Frontmatter](handbook-frontmatter.md) - §3 universal SKILL.md frontmatter and hard validator limits. Routes to [description budgets](handbook-description-budgets.md) for target bands, alias discipline, templates, the 2026-05-21 audit baseline.
* [Status lines and required sections](handbook-sections.md) - §4 the status line and its kind/emoji pairings, §5 required H2 sections per category plus the repo AGENTS.md heading set.
* [Validators and pre-commit wiring](handbook-validators.md) - §6 documentation-wide validators, `skill-conventions`, `dead-cross-links`, `em-dash-check`, pre-commit wiring.
* [Templates, cross-linking, categories, voice, symlinks](handbook-conventions.md) - §7 templates, §8 cross-linking rules, §9 adding a new category, §10 voice conventions, §11 symlinks and the global skill surface.

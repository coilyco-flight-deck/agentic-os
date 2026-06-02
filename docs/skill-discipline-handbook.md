# Skill Discipline Handbook

This handbook documents the skill-discipline rules enforced by the pre-commit hooks shipped from this repo. It pairs with [`skill-discipline-example-categories.yaml`](skill-discipline-example-categories.yaml) (the machine-readable spec) and the hooks declared in [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml).

If your repo follows this handbook, the hooks will pass. If they disagree, the spec is authoritative for the validator and this file should be updated to match.

The handbook is split across topic files to stay under the documentation size cap. Read them in order:

- [`skill-discipline-handbook-layout.md`](skill-discipline-handbook-layout.md) - layout and categories (sections 1-2).
- [`skill-discipline-handbook-frontmatter.md`](skill-discipline-handbook-frontmatter.md) - frontmatter, the status line, required sections (sections 3-5).
- [`skill-discipline-handbook-voice-size.md`](skill-discipline-handbook-voice-size.md) - voice rules (section 6).
- [`skill-discipline-handbook-size-caps.md`](skill-discipline-handbook-size-caps.md) - size caps (section 7).
- [`skill-discipline-handbook-crosslinks-why.md`](skill-discipline-handbook-crosslinks-why.md) - cross-links and encoding the why (sections 8-9).
- [`skill-discipline-handbook-hooks.md`](skill-discipline-handbook-hooks.md) - the hooks themselves (section 10).

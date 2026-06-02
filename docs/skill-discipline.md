# skill-discipline

Pre-commit hooks and authoring docs for documentation and skill repositories.

## Hooks

The validators live in the `agentic_os` Python package and ship through the managed `coilysiren/agentic-os` pre-commit block.

- `validate-skills.py` - validates `.agents/skills/` against a spec at `.agents/skills/categories.yaml`. Checks frontmatter, prefix taxonomy, status lines, required sections, size caps, stale skill-name references.
- `check-dead-links.py` - walks markdown inside `.agents/skills/`, fails if any inline `[text](path.md)` link does not resolve.
- `check-documentation-layout.py` - keeps Markdown at repo root, flat `docs/*.md`, or skill folders only.
- `check-code-comments.py` - keeps standalone code comments to one line, max 90 chars.
- `check-commit-closes-issue.py` - rejects commits whose message lacks a `closes #N` / `fixes #N` / `resolves #N` keyword pointing at an issue in the same repo. (Already canonical here; just listed for completeness.)

See [`skill-discipline-example-pre-commit-config.yaml`](skill-discipline-example-pre-commit-config.yaml) for the managed `.pre-commit-config.yaml` block.

## Docs

- [`skill-discipline-handbook.md`](skill-discipline-handbook.md) - the discipline these hooks enforce, with the why behind each rule.
- [`skill-discipline-authoring.md`](skill-discipline-authoring.md) - how to draft, validate, and ship a new skill.
- [`skill-discipline-example-categories.yaml`](skill-discipline-example-categories.yaml) - heavily commented spec to start from.
- [`skill-discipline-template-SKILL.md.template`](skill-discipline-template-SKILL.md.template) - minimal starter for a new skill.

# Skill Discipline Handbook - The Hooks

## 10. The three hooks

`.pre-commit-hooks.yaml` exposes three hooks. Wire each one explicitly in your repo's `.pre-commit-config.yaml`.

### check-skills (pre-commit, pre-push)

Runs `check-skills`. Checks frontmatter, prefix/exact match, status (where enforced), H1 pattern, required sections, forbidden body strings, stale skill-name backtick references, size caps. Symlinks under `.agents/skills/` are skipped, since their canonical target is validated where it lives.

### dead-cross-links (pre-commit, pre-push)

Runs `check-dead-links`. Walks every Markdown file under `.agents/skills/`, extracts inline `[text](target)` links, fails on any local-relative target that does not resolve to a real file. External URLs, anchors, placeholders (`...`, `TBD`, `TODO`), and paths escaping the repo are skipped.

### catalog-trifecta (pre-commit, pre-push)

Runs `check-catalog-trifecta`. Enforces the repo entrypoint set: `README.md`, `AGENTS.md`, `docs/FEATURES.md`, and one catalog YAML (`.coily/coily.yaml` or `.ward/ward.yaml`). Each Markdown file needs `## See also`, links to the other entrypoints, and the convention citation.

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

Runs `check-documentation-layout`. Enforces Markdown placement across the repo:

* root Markdown is limited to the universal allow-list (`README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE.md`);
* ordinary documentation lives in flat `docs/*.md`;
* skill documentation lives under `.agents/skills/`, `.agents/skills/`, or `skills/`;
* `docs/` has no subdirectories. Use filename prefixes when grouping is needed;
* every Markdown file stays under the size cap enforced by [`check_documentation_layout.py`](../agentic_os/pre_commit/check_documentation_layout.py). AGENTS.md and SKILL.md are not exempt.

### code-comments (pre-commit)

Runs `check-code-comments`. Enforces code-comment discipline for common source files: standalone comments are up to two contiguous lines, max 90 chars each. Longer durable explanation belongs in `docs/*.md`; code gets a short pointer only. YAML is stricter: a key-sorter would drift any lower comment off its target, so YAML allows just one comment line and only as the first line of the file.

### commit-closes-issue (commit-msg)

Runs `check-commit-closes-issue`. Reads the commit message and rejects it unless it references an issue in the same repo via its full Forgejo URL (`https://forgejo.coilysiren.me/<owner>/<repo>/issues/N`). A closing keyword (`closes` / `fixes` / `resolves`) in front is optional - the reference is what the rule requires, not the close. Bare `#N` / `owner/repo#N` keyword forms are rejected (they trigger GitHub auto-close on mirrored repos), as are Forgejo URLs pointing at a different repo. Merge / Revert / fixup! / squash! commits are exempt. (Loosening planned: eventually this fires only on commits merging into main.)

This hook is independent of skill authoring but ships in the same repo because it carries the same family of discipline: a small, automated gate that catches process drift before it lands.

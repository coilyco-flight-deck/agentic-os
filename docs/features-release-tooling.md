# Features: cross-repo tooling and release

Pre-commit baseline, diagnostics, and Forgejo-canonical release actions.

## Cross-repo pre-commit baseline

Ships the canonical hook IDs each `coilysiren/*` repo pins via `rev:`. The active set covers standard hygiene hooks, `actionlint`, `shellcheck`, and `typos`. `shfmt`, unresolved placeholders, and issue references stay opt-in in [pre-commit hygiene](pre-commit-hygiene.md); the manual guards live in [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml). Consumers don't vendor the validators. Package is pip-installed for pre-commit. Hooks and generators live in `agentic_os`.

## Seed-skill propagation

qwen-opencode's per-repo context management wants a little language context living inside each target repo (for a Python repo, a pointer to how Kai writes Python). The `coding-<lang>` skills declare how they propagate with a `seed:` frontmatter block: `kind: always` (the `coding-git` baseline, seeded into every repo) or `kind: language` with `language` + `extensions` (seeded into repos containing those files). Target repos reference a seeded skill by its canonical path, e.g. `.agents/skills/coding-python/SKILL.md`.

The frontmatter is the source of truth. `generate-seed-skills` renders it into `agentic_os/seed_skills_data.py`, shipped in the package so consumer repos enforce the `seed-skills` hook offline, and `check-seed-skills-drift` (dogfooded in `agentic-os` only) fails if that table goes stale. This repo ships the validator half only: the actual copying of skills into target repos is Ansible's job.

## Diagnostic + utility helpers

Single-purpose validators for cryptic failure modes. These plus [`ward context-budget`](context-budget.md) are CLI/on-demand tools, not repo-content hooks, so they ship as ward verbs (agentic-os#233):

- `ward aws-config` - catches the `[profile default]` trap (SDKs read `[default]`; a misplaced region surfaces later as a useless `NoRegion`).
- `ward ssm-path` - checks parameter paths against the `/<org>/<repo>/<tier>/<tail>` schema before IAM/KMS, where a malformed path silently misses every tier policy.
- Verbatim-echo wrapper that fences command output and clips to mobile-readable size, for the `$$ <cmd>` chat convention.
- GPG signing doctor that walks every check needed to diagnose `failed to sign the data` and names the likely fix per failure mode.

## Forgejo-canonical release actions

Composite Forgejo Actions for the brew release pipeline, each a forgejo-API-only replacement for a github-coupled marketplace action:

- `actions/tag-bump` - bump the latest semver tag by a fixed amount (minor by default, major hand-driven via the `bump` input), create the tag via forgejo Tags API. Does not parse commit messages. Replaces `mathieudutour/github-tag-action`.
- `actions/create-release` - POST to forgejo Releases API. Idempotent on tag collision. Replaces `softprops/action-gh-release` for the release-create step.
- `actions/bump-formula` - rewrite a Homebrew Formula's `url ".."` line to pin the new tag + revision and PUT via forgejo Contents API. Same-repo write only; cross-repo bumps live in the consuming repo.

Consumed via `uses: coilyco-flight-deck/agentic-os/actions/<name>@main` from a `.forgejo/workflows/*.yml`. The auto-issued `${{ github.token }}` per-job token covers same-repo writes; no extra secret to provision.

agentic-os dogfoods these actions for its own releases (`.forgejo/workflows/`), referencing them locally via `uses: ./actions/...` so the source repo never waits on its own mirror. Push to main cuts a minor tag + release, and a mirror job force-pushes to the read-only `coilysiren/agentic-os` GitHub mirror. The consumer pin is tag-derived at read time (`default_rev()`), so there is no per-push pin-bump commit (agentic-os#238). Major bumps stay hand-cut via `scripts/release.py`. A `workflow_dispatch` trigger re-fires it by hand on a missed push enqueue, no dummy commit (agentic-os#240). Walkthrough: [docs/release.md](release.md).

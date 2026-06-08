# Features: cross-repo tooling and release

Pre-commit baseline, diagnostic helpers, and Forgejo-canonical release actions.

## Cross-repo pre-commit baseline

Ships the canonical hook IDs that every `coilysiren/*` repo pins via `rev:`: catalog doc-size enforcement, README/AGENTS/FEATURES trifecta presence, documentation layout, agent context load-point hygiene (pure-pointer CLAUDE.md, no forked rungs, `@AGENTS.md` bridge), code-comment discipline, skill structural validation, dead cross-link detection, the `catalog-block-present` check, the `agents-pointer` managed-block check ([details](features-agents-pointer.md)), and a `misplaced-skills` guard (opt-in via `[tool.agentic-os.misplaced-skills]` deny/allow globs) that fails when a repo hosts a skill owned by another repo, a `merge-conflicts` guard that rejects staged files still carrying conflict markers (so a conflicted security-config script never commits broken), a `seed-skills` guard (opt-in via `[tool.agentic-os.seed-skills]`) that fails when a repo contains code in a language whose `coding-<lang>` seed skill it does not reference, and the agent-compose source guards (per-source and aggregate size budget, cross-source/cascade dedup, composed-file drift). Consumers don't stamp local copies of the validators; the `agentic-os` Python package is pip-installed into each repo's pre-commit env. Rolled out and audited from `agentic-os-kai`.

## Seed-skill propagation

OpenClaw's per-repo context management wants a little language context living inside each target repo (for a Python repo, a pointer to how Kai writes Python). The `coding-<lang>` skills declare how they propagate with a `seed:` frontmatter block: `kind: always` (the `coding-git` baseline, seeded into every repo) or `kind: language` with `language` + `extensions` (seeded into repos containing those files). Target repos reference a seeded skill by its canonical path, e.g. `.agents/skills/coding-python/SKILL.md`.

The frontmatter is the source of truth. `generate-seed-skills` renders it into `agentic_os/seed_skills_data.py`, shipped in the package so consumer repos enforce the `seed-skills` hook offline, and `check-seed-skills-drift` (dogfooded in `agentic-os` only) fails if that table goes stale. This repo ships the validator half only: the actual copying of skills into target repos is Ansible's job.

## Diagnostic + utility helpers

Small, single-purpose scripts that exist because the failure modes they handle are cryptic by default:

- AWS config linter that catches the `[profile default]` trap (SDKs read `[default]`, misplaced region surfaces later as a useless `NoRegion`).
- Verbatim-echo wrapper that fences command output and clips to mobile-readable size, for the `$$ <cmd>` chat convention.
- GPG signing doctor that walks every check needed to diagnose `failed to sign the data` and names the most-likely fix per failure mode.

## Forgejo-canonical release actions

Composite Forgejo Actions for the brew release pipeline now that `forgejo.coilysiren.me` is canonical source. Three actions, each a forgejo-API-only replacement for a github-coupled marketplace action:

- `actions/tag-bump` - bump the latest semver tag by a fixed amount (minor by default, major hand-driven via the `bump` input), create the tag via forgejo Tags API. Does not parse commit messages. Replaces `mathieudutour/github-tag-action`.
- `actions/create-release` - POST to forgejo Releases API. Idempotent on tag collision. Replaces `softprops/action-gh-release` for the release-create step.
- `actions/bump-formula` - rewrite a Homebrew Formula's `url ".."` line to pin the new tag + revision and PUT via forgejo Contents API. Same-repo write only; cross-repo bumps live in the consuming repo.

Consumed via `uses: coilyco-flight-deck/agentic-os/actions/<name>@main` from a `.forgejo/workflows/*.yml`. Auto-issued `${{ github.token }}` (forgejo's compatibility name for its per-job token) covers same-repo writes; no extra secret to provision.

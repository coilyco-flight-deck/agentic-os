# Features: cross-repo tooling and release

Pre-commit baseline, diagnostic helpers, and Forgejo-canonical release actions.

## Cross-repo pre-commit baseline

Ships the canonical hook IDs that every `coilysiren/*` repo pins via `rev:`: catalog doc-size enforcement, README/AGENTS/FEATURES trifecta presence, documentation layout, agent context load-point hygiene (pure-pointer CLAUDE.md, no forked rungs, `@AGENTS.md` bridge), code-comment discipline, skill structural validation, dead cross-link detection, `closes #N` commit-msg enforcement, the `catalog-block-present` check, and a `misplaced-skills` guard (opt-in via `[tool.agentic-os.misplaced-skills]` deny/allow globs) that fails when a repo hosts a skill owned by another repo. Consumers don't stamp local copies of the validators; the `agentic-os` Python package is pip-installed into each repo's pre-commit env. Rolled out and audited from `agentic-os-kai`.

## Diagnostic + utility helpers

Small, single-purpose scripts that exist because the failure modes they handle are cryptic by default:

- AWS config linter that catches the `[profile default]` trap (SDKs read `[default]`, misplaced region surfaces later as a useless `NoRegion`).
- Verbatim-echo wrapper that fences command output and clips to mobile-readable size, for the `$$ <cmd>` chat convention.
- GPG signing doctor that walks every check needed to diagnose `failed to sign the data` and names the most-likely fix per failure mode.

## Forgejo-canonical release actions

Composite Forgejo Actions for the brew release pipeline now that `forgejo.coilysiren.me` is canonical source. Three actions, each a forgejo-API-only replacement for a github-coupled marketplace action:

- `actions/tag-bump` - parse conventional commits, compute the next semver, create the tag via forgejo Tags API. Replaces `mathieudutour/github-tag-action`.
- `actions/create-release` - POST to forgejo Releases API. Idempotent on tag collision. Replaces `softprops/action-gh-release` for the release-create step.
- `actions/bump-formula` - rewrite a Homebrew Formula's `url ".."` line to pin the new tag + revision and PUT via forgejo Contents API. Same-repo write only; cross-repo bumps live in the consuming repo.

Consumed via `uses: coilysiren/agentic-os/actions/<name>@main` from a `.forgejo/workflows/*.yml`. Auto-issued `${{ github.token }}` (forgejo's compatibility name for its per-job token) covers same-repo writes; no extra secret to provision.

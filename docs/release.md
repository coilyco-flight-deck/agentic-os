# Release pipeline

Forgejo-canonical release on push to `main`
(`forgejo.coilysiren.me/coilyco-flight-deck/agentic-os`). `.forgejo/workflows/release.yml`
now computes the next tag first, publishes and verifies the dev-base image, and
only then cuts the public git/release tag so no announcement can outlive a
missing manifest.

agentic-os is consumed as pre-commit hooks pinned by `rev:` tag, not a brew
formula or a prebuilt binary, so there is nothing to attach to the release and
no formula to bump - the only downstream artifact is the git tag itself.

## Why not release-please

release-please is PR-driven, and `coilysiren/agentic-os` has
`hasPullRequestsEnabled = false` on GitHub (the no-PR-on-GitHub stance). Rather
than port release-please to Forgejo, agentic-os reuses the forgejo-API-only
composite actions it already ships for the rest of the fleet (ward, cli-guard,
ward-kdl, ...). No PR, no manifest config, no GitHub API calls. The decision and
its alternatives are recorded in the issue this pipeline closed.

## Version bump

`actions/tag-bump` runs with no bump input, so every push-to-main release is a
minor bump. Commit messages are never parsed. For a major, run
`scripts/release.py --bump major` to cut `vN.0.0` by hand (its commit carries
`[skip ci]`). The actions are referenced locally (`uses: ./actions/...`).

`actions/tag-bump` also has a compute-only mode. That lets the workflow derive
the next semver, verify the pushed manifest, and only then create the public
tag and Forgejo release.

## Manual re-run (enqueue-miss recovery)

A `workflow_dispatch` trigger re-fires the pipeline by hand from the Forgejo
Actions tab, no dummy commit. It is the recovery lever for agentic-os#240, where
Forgejo missed a push enqueue and `v0.62.0` was hand-cut. Its `bump` input
defaults to `minor` and feeds `tag-bump` directly.

## Consumer pin (derived from the tag)

The tag every consumer repo inherits when `apply-agentic-os-hooks` rolls out the
hook block is resolved from the **latest git tag at read time**, not a committed
constant. `default_rev()` in `scripts/apply-agentic-os-hooks.py` reads
`git tag --list 'v*'` and falls back to `FALLBACK_REV` only when no tag is
fetched.

Deriving the pin from the tag is the point of agentic-os#238: tags are refs,
not tracked files, so cutting a release needs no followup bump commit. That
removed the old `bump-pin` job and its `CI_RELEASE_TOKEN` push. Now the release
is just the tag.

pyproject `version`, `uv.lock`, and the `FALLBACK_REV` floor are reconciled on
hand-cut releases by `scripts/release.py`, so they track major bumps and may
lag the tag between majors. That lag is cosmetic: consumers pin by git rev, and
`FALLBACK_REV` is only read when no tag is present.

## Mirror to GitHub

`.forgejo/workflows/mirror-to-github.yml` fast-forwards Forgejo `main` + `v*`
tags onto the read-only GitHub mirror (`coilysiren/agentic-os`) where the
fleet's `uses:` refs resolve. It is fast-forward-only (never `--force`, which
GitHub branch protection rejects) and no-ops without the PAT. See
[mirror-to-github.md](mirror-to-github.md) for details.

## Skip markers

`scripts/release.py`'s version commit carries `[skip ci]` so the hand-cut bump
does not re-trigger the workflow. The auto-pipeline no longer pushes a pin
commit at all. Shared composite actions live under `actions/*` in this repo.

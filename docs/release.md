# Release pipeline

Forgejo-canonical release on push to `main`
(`forgejo.coilysiren.me/coilyco-flight-deck/agentic-os`). agentic-os dogfoods
the composite actions it ships: `.forgejo/workflows/release.yml` cuts the tag +
release, then advances the in-repo consumer pin so downstream repos can pick up
the new tag through their normal upgrade flow.

agentic-os is consumed as pre-commit hooks pinned by `rev:` tag, not a brew
formula or a prebuilt binary, so there is nothing to attach to the release and
no formula to bump - the only downstream artifact is the git tag itself.

## Why not release-please

release-please is PR-driven, and `coilysiren/agentic-os` has
`hasPullRequestsEnabled = false` on GitHub (the no-PR-on-GitHub stance). Rather
than port release-please to Forgejo, agentic-os reuses the forgejo-API-only
composite actions it already ships for the rest of the fleet (ward, cli-guard,
coily, ...). No PR, no manifest config, no GitHub API calls. The decision and
its alternatives are recorded in the issue this pipeline closed.

## Version bump

`actions/tag-bump` runs with no bump input, so every push-to-main release is a
minor bump. Commit messages are never parsed - nothing in history can escalate
the bump. For a major, run `scripts/release.py --bump major` to cut `vN.0.0` by
hand (its commit carries `[skip ci]`, so it does not double-fire this pipeline);
pushes resume minor from there. The actions are referenced locally
(`uses: ./actions/...`), so the source repo never waits on its own GitHub mirror
being current to release.

## Consumer pin (bump-pin job)

`DEFAULT_REV` in `scripts/apply-agentic-os-hooks.py` is the tag every consumer
repo inherits when `apply-agentic-os-hooks` rolls out the hook block. The
`bump-pin` job rewrites it to the freshly cut tag via the Forgejo Contents API
and pushes a `[skip ci]` commit, so the rollout always pins the latest release.
This is the direct analog of ward's formula `url` bump. It needs the
`CI_RELEASE_TOKEN` Actions secret (the `write:repository` PAT set org-wide on
`coilyco-flight-deck`); without it the job logs and no-ops (the pin just stays
put until the secret is provisioned).

pyproject `version` and `uv.lock` are NOT touched by the auto-pipeline - keeping
the job a single-file write avoids a `uv` dependency in the runner and any
`uv.lock` drift. They are reconciled on hand-cut releases by
`scripts/release.py`, so they track major bumps and may lag the tag between
majors. That lag is cosmetic: consumers pin by git rev, not by the package
version.

## Mirror to GitHub

`.forgejo/workflows/mirror-to-github.yml` force-pushes Forgejo `main` + `v*` tags
to the read-only GitHub mirror (`coilysiren/agentic-os`), which is where the
fleet's `uses: coilysiren/agentic-os/actions/*@main` references resolve. It
no-ops without the `GITHUB_MIRROR_PAT` secret. Forgejo is upstream-of-record;
GitHub is the PR-gated downstream mirror.

## Skip markers

Both the `bump-pin` pin commit and `scripts/release.py`'s version commit carry
`[skip ci]` so the bump does not re-trigger the workflow. Shared composite
actions live under `actions/*` in this repo. This replaces the deleted
`.github/workflows` release; building moved off GitHub Actions onto Forgejo.

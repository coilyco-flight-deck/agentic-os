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
ward-kdl, ...). No PR, no manifest config, no GitHub API calls. The decision and
its alternatives are recorded in the issue this pipeline closed.

## Version bump

`actions/tag-bump` runs with no bump input, so every push-to-main release is a
minor bump. Commit messages are never parsed - nothing in history can escalate
the bump. For a major, run `scripts/release.py --bump major` to cut `vN.0.0` by
hand (its commit carries `[skip ci]`, so it does not double-fire this pipeline);
pushes resume minor from there. The actions are referenced locally
(`uses: ./actions/...`), so the source repo never waits on its own GitHub mirror
being current to release.

## Manual re-run (enqueue-miss recovery)

A `workflow_dispatch` trigger re-fires the pipeline by hand from the Forgejo
Actions tab, no dummy commit. It is the recovery lever for agentic-os#240, where
Forgejo missed a push enqueue and `v0.62.0` was hand-cut: when a push lands but
no run appears, dispatch against `main`. Its `bump` input defaults to `minor` and
feeds `tag-bump` directly.

## Consumer pin (derived from the tag)

The tag every consumer repo inherits when `apply-agentic-os-hooks` rolls out the
hook block is resolved from the **latest git tag at read time**, not a committed
constant. `default_rev()` in `scripts/apply-agentic-os-hooks.py` reads
`git tag --list 'v*'` from the checkout and returns the highest version, falling
back to the `FALLBACK_REV` floor only when no tag is fetched (a shallow clone).

Deriving the pin from the tag is the whole point of agentic-os#238: tags are
refs, not tracked files, so cutting a release needs no followup bump commit.
That removed the old `bump-pin` job (and its `CI_RELEASE_TOKEN` Contents-API
push), which used to land a `chore: bump DEFAULT_REV to vX.Y.Z [skip ci]` commit
on every push to main - the commit that left every local checkout "1 behind
origin/main" and blocked ward's clean+synced gate. Now the release is just the
tag.

pyproject `version`, `uv.lock`, and the `FALLBACK_REV` floor are reconciled on
hand-cut releases by `scripts/release.py`, so they track major bumps and may lag
the tag between majors. That lag is cosmetic: consumers pin by git rev (now
tag-derived), not by the package version, and `FALLBACK_REV` is only read when
no tag is present.

## Mirror to GitHub

`.forgejo/workflows/mirror-to-github.yml` force-pushes Forgejo `main` + `v*` tags
to the read-only GitHub mirror (`coilysiren/agentic-os`), which is where the
fleet's `uses: coilysiren/agentic-os/actions/*@main` references resolve. It
no-ops without the `GITHUB_MIRROR_PAT` secret. Forgejo is upstream-of-record;
GitHub is the PR-gated downstream mirror.

## Skip markers

`scripts/release.py`'s version commit carries `[skip ci]` so the hand-cut bump
does not re-trigger the workflow. The auto-pipeline no longer pushes a pin
commit at all (the consumer pin is tag-derived), so there is nothing per-push to
skip. Shared composite actions live under `actions/*` in this repo. This
replaces the deleted `.github/workflows` release; building moved off GitHub
Actions onto Forgejo.

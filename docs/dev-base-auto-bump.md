# dev-base dependency planner

The dev-base Dockerfile pins every tool as a hand-edited `ARG`
([docs/dev-base-image.md](dev-base-image.md)). `promote.yml` republishes the
dev-base graph on every relevant push to main before `release` moves, but nothing kept
those pins current, so the images drifted behind upstream until a human edited an `ARG`.
That is the ward#288/#301 incident (agentic-os#272): headless agents kept
hitting a bug already fixed upstream because the image they ran predated the
fix.

## What runs

[`.forgejo/workflows/dep-bump.yml`](../.forgejo/workflows/dep-bump.yml) runs
daily (and on `workflow_dispatch`). It calls
[`scripts/dep-bump.py`](../scripts/dep-bump.py), which resolves each pinned tool
against its upstream latest release, and for every pin that drifted commits a
single `ARG` bump and pushes to main. A language pin rebuilds its owning payload
and the full fan-in. A shared or internal-tool pin reuses the cached language
payloads and rebuilds the full surface. Only the full image receives the moving
`:release` alias.

The bump logic lives in this repo because the publish pipeline does (AGENTS.md).
Fleet rollout is not its concern.

After the planned bumps are applied, the workflow runs the same gate as release
before it pushes, so a bad pin leaves the run red and stops before `main`.

## Properties

* **Auditable, not silent.** One commit per tool
  (`chore(dev-base): bump UV_VERSION 0.11.21 -> 0.11.24`), so history shows every
  bump and a bad one bisects to its own commit.
* **Conservative bumps.** Node and the .NET SDK track the latest release of their
  currently-pinned major (no surprise major jump - the SDK stays on .NET 10,
  agentic-os#329); uv, go, aws-cli, claude, mcporter, codex, goose, gh, helm,
  kubectl, yq, docker, tailscale, and trufflehog track latest stable.
  Tailscale resolves against its `pkgs.tailscale.com/stable` feed (not GitHub
  tags, which interleave the unstable odd-minor releases). A hand-edited `ARG`
  wins until upstream passes it.
* **Promoted internal tools.** `SPECGEN_VERSION` and `WARD_VERSION` resolve the
  generated `v*` tag attached to each repository's `release` branch. Raw tags
  ahead of that commit remain staging and never enter the production image.
* **Unmanaged pins remain visible.** AOS, OpenCode, Git LFS, Trunk,
  `GOLANGCI_LINT_VERSION`, and `KDLFMT_VERSION` currently have no resolver.
  Their pins require an explicit inventory. `docker buildx` and `wasm-pack`
  stay job-local, so dev-base does not claim them. The keep-or-retire decision
  for this partial planner is tracked in agentic-os#865.
* **Fail-soft.** A resolver whose upstream is unreachable or has reshaped its API
  drops from that run with a warning. It never blocks the other bumps.
* **Scoped inventory.** The planner reports only pins with an implemented
  resolver. It is not proof that every Dockerfile pin is current. Unmanaged pins
  still require an explicit inventory against their owning upstream.

## Running it locally

* `ward exec dep-bump -- check` - drift summary, exit 1 if any pin is stale.
* `ward exec dep-bump -- plan` - the stale set as TSV (`--json` for machines).
* `ward exec dep-bump -- apply --arg UV_VERSION --version X` - rewrite one `ARG`.

## Republish token

The workflow pushes with the auto-issued job token by default, which is enough on
a Forgejo that enqueues workflow runs from bot-token pushes. If your Forgejo
suppresses them, the bump lands but the release promotion never fires. Set the
`DEP_BUMP_TOKEN` Actions secret to a `coilyco-ops`-owned `write:repository`
PAT so the push is attributed to a real user and reliably reaches the
promotion flow.
[`scripts/rotate-dep-bump-token.sh`](../scripts/rotate-dep-bump-token.sh) mints
and sets it (mirrors the `REGISTRY_TOKEN` rotation in dev-base-image.md).

## See also

* [docs/dev-base-image.md](dev-base-image.md) - the image and its publish path.
* [docs/release.md](release.md) - the release pipeline the republish rides on.

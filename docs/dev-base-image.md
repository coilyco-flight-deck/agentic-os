# dev-base container image

aos owns the agent dev environment. ward consumes it by tag, so config cannot
drift.

This page describes the current published `dev-base-full` contract. The tier
layout that keeps this default while reducing rebuild blast radius is in
[Tiered dev-base image split](dev-base-image-tiering.md).

## What ships

[`docker/dev-base/core/Dockerfile`](../docker/dev-base/core/Dockerfile) layers
the root runtime tier on `ubuntu:24.04`. The sibling tier Dockerfiles live in
[`docker/dev-base/`](../docker/dev-base/) as one folder per tier, each with the
literal filename `Dockerfile`.

- **core toolchain** - `uv`, pre-commit, Python, shellcheck, git, git-lfs, build-essential, Rust, and ward.
- **language/runtime tiers** - Node, Go, and .NET 10 + ICU.
- **ops / agent CLIs** - aws cli, Homebrew, claude, mcporter, opencode, codex, goose, gh, helm, kubectl, yq, Docker CLI, and Tailscale CLI.
- **gate tools** - golangci-lint, trufflehog, and kdlfmt.
- **platform seed** - the public substrate mirrors, the baked agent self-name / status-line assets, and the container shell entrypoint that seeds `AOS_REPO_ROOT` plus `WARD_CONFIG_REF` before the read-only director shell starts.

Tools under `/usr/local`, `/home/linuxbrew/.linuxbrew`, or `/opt` run as any uid. ward owns `run-as-uid`, mounts, and `~/.aws`. Root bootstrap seeds `/home/ubuntu/.ward/audit` as uid 1000 and avoids root-owned audit state.

## Naming and tags

Published as one package,
`forgejo.coilysiren.me/coilyco-flight-deck/agentic-os`, with variants as tags.
`full` is the plain default tag, and the folder name prefixes every other tier's
tag, so the published refs are `agentic-os:${TAG}`, `agentic-os:core-${TAG}`,
`agentic-os:lang-node-${TAG}`, and so on. Each tier also carries a moving alias
named for the publishing branch (`agentic-os:release` and `agentic-os:core-release`
in the two-stage flow), each release uses one `vX.Y.Z`, and the `buildcache` tags
hold the cache. `:latest` and the old `agentic-os-<tier>` package names are
retired.

## How it publishes

The release jobs in [`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml)
compute the tag, cut it, and only then publish the images (aos#490 inverted
the old images-before-tag order). `publish-dev-base` calls
[`scripts/dev-base-build.py`](../scripts/dev-base-build.py), which derives the
ordered tier plan from the folder layout and builds `core -> lang-node ->
lang-go -> lang-dotnet -> ops -> agent -> full` in order. Each pushed tier
retries, so a flaky blob write re-pushes a tier, not the run. The core image
stamps
`WARD_CONFIG_REF` from the current agentic-os commit at build time, so ward
launches against the exact bundled `.ward/` checkout rather than a moving
`main`. The core build runs `ward doctor` after installing ward, which rejects a
broken bundled config before the image publishes.

The base apt layer retries against mirror drift so a publish can still land when Ubuntu package metadata and archives briefly disagree.

## Pinning a tool

Versions pin as `ARG`s: hand-edit and push to main to pin or roll back, else a
scheduled **auto-bump** refreshes stale pins ([auto-bump doc](dev-base-auto-bump.md)).
`GOLANGCI_LINT_VERSION` and `KDLFMT_VERSION` opt out, bumped by hand.

## Pulling it

```bash
docker pull forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:release
```

Needs a `docker login`; `ward container up/exec` (ward#98) is the entry point.

## Not here

- Mount / compose logic and `ward container` verbs - ward#98; the mount-eligibility manifest - aos#222.
- `coily` (retired, folded into `ward ops`) and running services - not shipped.
- `docker buildx` and `wasm-pack` - job-local publish or toolchain steps.

## See also

- [release.md](release.md) - the pipeline this rides on; [FEATURES.md](FEATURES.md).
- [Tiered dev-base image split](dev-base-image-tiering.md) - the implemented fan-out
  and fan-in model that preserves `dev-base-full` as the default.

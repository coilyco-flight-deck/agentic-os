# dev-base container image

aos owns the agent dev environment. ward consumes it by tag, so config cannot
drift.

This page describes the current published `dev-base-full` contract. The
tiering design that keeps this default while reducing rebuild blast radius is
in [Tiered dev-base image design](dev-base-image-tiering.md).

## What ships

[`docker/dev-base/Dockerfile`](../docker/dev-base/Dockerfile) layers the
toolchain on `ubuntu:24.04`:

- **uv + managed Pythons** - Python project/tool manager; 3.13 + 3.12 pre-installed in a writable `UV_PYTHON_INSTALL_DIR` (agentic-os#327).
- **pre-commit** - the catalog hook driver (a uv tool).
- **python3 + shellcheck + git + git-lfs + build-essential** - direct needs and hook shell-outs.
- **node + npm** - Claude Code's runtime.
- **go** - builds the `warp/` hooks and the ward binary below.
- **Rust toolchain** - `cargo` and `rustc` are on PATH for Rust workspaces.
- **.NET SDK 10 + ICU** - C# mods compile in-container with full ICU globalization (`libicu74`) not invariant mode (agentic-os#329).
- **aws cli v2** - SSM secret loader + `~/.aws` passthrough; region defaults `us-east-1` (agentic-os#286).
- **Homebrew** - Linux Homebrew at `/home/linuxbrew/.linuxbrew`, on `PATH`.
- **claude + mcporter + opencode + codex + goose** - agent CLIs plus **docker cli + socat** for `warded #N` dispatch.
- **gh + helm + kubectl + yq** - CI CLIs for sync, chart, deploy, and manifests.
- **ward** - the dev-command surface agents route through (`ward <verb>`), built from source at pinned `WARD_VERSION`.
- **golangci-lint + trufflehog + kdlfmt** - lint / secret-scan / format binaries the gate shells out to.
- **tailscale cli** - tailnet client (no daemon) so a credentialed container reaches the tower; auth stays ward's axis (agentic-os#286).
- **public substrate seed** - mirrors of the image-tier reference repos at `/opt/substrate-seed`.
- **in-container agent self-name** - baked `agent-name.sh` so warded agents self-name ([doc](dev-base-self-name.md)).

Tools under `/usr/local`, `/home/linuxbrew/.linuxbrew`, or `/opt` run as any uid. ward owns `run-as-uid`, mounts, and `~/.aws`. Root bootstrap seeds `/home/ubuntu/.ward/audit` as uid 1000 and avoids root-owned audit state.

## Naming and tags

Published under
`forgejo.coilysiren.me/coilyco-flight-deck/agentic-os` as a tiered family. The
release workflow publishes the tier refs there, `dev-base-full` keeps
`:latest`, and each release uses one `vX.Y.Z`; `:buildcache` holds the cache.

## How it publishes

The release jobs in [`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml) run before the public tag exists. They publish core first, fan out sibling tier targets in parallel, and publish `dev-base-full` last. The release tag lands only after the set has been pushed and verified.

The tag comes last, after the image has been built, pushed, and verified.
The base apt layer retries against mirror drift so a publish can still land when Ubuntu package metadata and archives briefly disagree.

## Pinning a tool

Versions pin as `ARG`s: hand-edit and push to main to pin or roll back, else a
scheduled **auto-bump** refreshes stale pins ([auto-bump doc](dev-base-auto-bump.md)).
`GOLANGCI_LINT_VERSION` and `KDLFMT_VERSION` opt out, bumped by hand.

## Pulling it

```bash
docker pull forgejo.coilysiren.me/coilyco-flight-deck/agentic-os-full:latest
```

Needs a `docker login`; `ward container up/exec` (ward#98) is the entry point.

## Not here

- Mount / compose logic and `ward container` verbs - ward#98; the mount-eligibility manifest - aos#222.
- `coily` (retired, folded into `ward ops`) and running services - not shipped.
- `docker buildx` and `wasm-pack` - job-local publish or toolchain steps.

## See also

- [release.md](release.md) - the pipeline this rides on; [FEATURES.md](FEATURES.md).
- [Tiered dev-base image design](dev-base-image-tiering.md) - the planned fan-out
  and fan-in model that preserves `dev-base-full` as the default.

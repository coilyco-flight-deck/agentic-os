# dev-base container image

aos owns the agent dev environment as a published artifact, the analog of the
ward / coily brew binaries: a thing you pull, not build-from-source on demand.
ward consumes it by tag and never touches the Dockerfile, so no repo needs
cloning to know how to run its container and config cannot drift across repos.

Part of the dockerized-local-dev epic ([agentic-os#220](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/220)),
ticket [#221](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/221).

## What ships

[`docker/dev-base/Dockerfile`](../docker/dev-base/Dockerfile) layers the
inner-loop toolchain on an `ubuntu:24.04` base:

- **uv** - Python project + tool manager.
- **pre-commit** - the catalog hook driver (a uv tool).
- **python3 + shellcheck + git + build-essential** - direct needs and what the catalog hooks shell out to.
- **node + npm** - Claude Code's runtime.
- **go** - builds the `warp/` module's hooks (and, later, ward + coily).
- **aws cli v2** - the SSM secret loader and `~/.aws` passthrough.
- **claude** - the agent, pinned.

Every tool installs world-readable under `/usr/local` or `/opt` so the image
runs as any uid. ward owns the run-as-uid, mount set, and `~/.aws` passthrough
at run time, so the image bakes in no user and no repo source. lore / aos / aosk
and task repos are bind-mounted by `ward container`, not copied in.

## Naming and tags

Published to the forgejo registry as
`forgejo.coilysiren.me/coilyco-flight-deck/agentic-os`. Each release tags the
image with the release version (`vX.Y.Z`) and moves `:latest`, so the version
tracks the repo's release the way `DEFAULT_REV` does and a consumer pin plus its
image are one version. A `:buildcache` tag holds the layer cache, not for pulling.

## How it publishes

The `publish-image` job in [`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml)
runs after a release cuts a tag, on the DinD `docker` runner: install the docker
CLI + buildx plugin, resolve the in-cluster daemon, `docker login` with the
auto-issued Actions job token (the job requests `packages: write`, so no PAT is
needed), stand up qemu + a `docker-container` builder, then
`buildx build --platform linux/amd64,linux/arm64 ... --push` with a registry
layer cache, tagging `:vX.Y.Z` and `:latest`.

Multi-arch means arm64 Macs and amd64 Linux hosts each pull a native image. The
layer cache keeps an unchanged Dockerfile's republish cheap even though every
push to main cuts a release. If arm64 emulation turns flaky, drop `linux/arm64`
from `PLATFORMS`; amd64 matches the runner.

## Pinning a tool

Versions are pinned as `ARG`s atop the Dockerfile. To bump one, edit its `ARG`
default and push to main; the next release republishes the tag. Current pins
were resolved against upstream on 2026-06-15.

## Pulling it

```bash
docker pull forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:latest
```

Needs a one-time `docker login forgejo.coilysiren.me`. The `ward container
up/exec` wrapper (ward#98) is the intended entry point; raw `docker run` is for
poking at the image directly.

## Not here

- Mount / compose logic and the `ward container` verbs - ward#98.
- The mount-eligibility manifest - aos #222.
- ward + coily in the image - a fast follow (needs a cross-repo build token).
- Running services in containers - a later effort.

## See also

- [docs/release.md](release.md) - the release pipeline this rides on.
- [docs/FEATURES.md](FEATURES.md) - capability inventory.

# dev-base container image

aos owns the agent dev environment as a published artifact - the analog of the
ward brew binary, pulled not built from source. ward consumes it by tag and never
touches the Dockerfile, so config cannot drift across repos. Part of the
dockerized-local-dev epic ([agentic-os#220](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/220)).

## What ships

[`docker/dev-base/Dockerfile`](../docker/dev-base/Dockerfile) layers the
inner-loop toolchain on `ubuntu:24.04`:

- **uv** - Python project + tool manager.
- **pre-commit** - the catalog hook driver (a uv tool).
- **python3 + shellcheck + git + build-essential** - direct needs and catalog-hook shell-outs.
- **node + npm** - Claude Code's runtime.
- **go** - builds the `warp/` module's hooks (and, later, ward).
- **aws cli v2** - SSM secret loader + `~/.aws` passthrough; `AWS_DEFAULT_REGION` / `AWS_REGION` default to `us-east-1` so SSM resolves given creds (agentic-os#286).
- **claude + codex + goose** - pinned agent CLIs; plus the **docker cli + socat** for `explore`'s sibling `warded #N` dispatch (ward#315), inert elsewhere.
- **golangci-lint + trufflehog + kdlfmt** - the lint / secret-scan / format binaries the pre-commit and CI gate shell out to, so an agent self-runs the gate in-container instead of hand-fetching them mid-run (agentic-os#292). golangci-lint + kdlfmt are hand-pinned to the consumers' CI versions, trufflehog auto-bumps - see [dev-base-auto-bump.md](dev-base-auto-bump.md).
- **tailscale cli** - tailnet client binary (no daemon) so a credentialed container reaches the tower over the tailnet; tailnet auth stays ward's separate axis (agentic-os#286).
- **public substrate seed** - bare mirrors of the image-tier reference repos at `/opt/substrate-seed` ([list](../docker/dev-base/substrate-image-repos.txt)), so a cold gitcache hydrates with no network. Only public repos baked.
- **in-container agent self-name** - baked `agent-name.sh` + policy `managed-settings.json` so warded agents self-name like host sessions ([dev-base-self-name.md](dev-base-self-name.md)).

Every tool installs world-readable under `/usr/local` or `/opt`, so the image runs
as any uid. ward owns the run-as-uid, mounts, and `~/.aws` passthrough; it bakes
in no user and no **target** repo (cloned fresh at run).

## Naming and tags

Published to the forgejo registry as
`forgejo.coilysiren.me/coilyco-flight-deck/agentic-os`. Each release tags `vX.Y.Z`
and moves `:latest`, so a pin and its image share a version; a `:buildcache` tag
holds the layer cache.

## How it publishes

The `publish-image` job in [`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml)
runs after a release cuts a tag, on the DinD `docker` runner: `docker login` with
the `REGISTRY_TOKEN` secret, then `buildx build --platform linux/amd64,linux/arm64
... --push` with a registry layer cache, tagging `:vX.Y.Z` and `:latest`. So each
arch pulls a native image and an unchanged Dockerfile republishes off the cache.
`REGISTRY_TOKEN` is a `coilyco-ops` `write:package` PAT;
[`rotate-registry-token.sh`](../scripts/rotate-registry-token.sh) re-mints it.

## Pinning a tool

Versions are pinned as `ARG`s. Edit one by hand and push to main to pin or roll
back; a scheduled **auto-bump** otherwise refreshes stale pins
([auto-bump doc](dev-base-auto-bump.md)). `GOLANGCI_LINT_VERSION` and
`KDLFMT_VERSION` opt out of it on purpose, bumped by hand.

## Pulling it

```bash
docker pull forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:latest
```

Needs a one-time `docker login forgejo.coilysiren.me`; `ward container up/exec`
(ward#98) is the intended entry point.

## Not here

- Mount / compose logic and `ward container` verbs - ward#98; the mount-eligibility manifest - aos#222.
- ward in the image - a fast follow (needs a cross-repo build token); running services - a later effort.

## See also

- [release.md](release.md) - the pipeline this rides on. Inventory: [FEATURES.md](FEATURES.md).

# dev-base container image

aos owns the agent dev environment as a published artifact - the analog of the
ward brew binary, pulled not built. ward consumes it by tag and never touches the
Dockerfile, so config cannot drift. Part of the dockerized-local-dev epic
([agentic-os#220](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/220)).

## What ships

[`docker/dev-base/Dockerfile`](../docker/dev-base/Dockerfile) layers the
inner-loop toolchain on `ubuntu:24.04`:

- **uv** - Python project + tool manager.
- **pre-commit** - the catalog hook driver (a uv tool).
- **python3 + shellcheck + git + build-essential** - direct needs and catalog-hook shell-outs.
- **node + npm** - Claude Code's runtime.
- **go** - builds the `warp/` module's hooks and the ward binary below.
- **aws cli v2** - SSM secret loader + `~/.aws` passthrough; `AWS_DEFAULT_REGION` / `AWS_REGION` default to `us-east-1` so SSM resolves (agentic-os#286).
- **claude + codex + goose** - pinned agent CLIs; plus **docker cli + socat** for `explore`'s sibling `warded #N` dispatch (ward#315), inert elsewhere.
- **ward** - the dev-command surface agents route through (`ward <verb>`), built from source at the pinned `WARD_VERSION` tag so it is baked in, not `go install`-ed per run. Its source and `cli-guard` dep are public, so the build clones anonymously with **no build token** (agentic-os#223); `coily` is not shipped.
- **golangci-lint + trufflehog + kdlfmt** - the lint / secret-scan / format binaries the gate shells out to, so an agent self-runs it in-container (agentic-os#292); pinning in [dev-base-auto-bump.md](dev-base-auto-bump.md).
- **tailscale cli** - tailnet client (no daemon) so a credentialed container reaches the tower; tailnet auth stays ward's separate axis (agentic-os#286).
- **public substrate seed** - bare mirrors of the image-tier reference repos at `/opt/substrate-seed` ([list](../docker/dev-base/substrate-image-repos.txt)), so a cold gitcache hydrates offline (public repos only).
- **in-container agent self-name** - baked `agent-name.sh` + policy `managed-settings.json` so warded agents self-name like host sessions ([doc](dev-base-self-name.md)).

Every tool installs world-readable under `/usr/local` or `/opt`, so the image runs
as any uid. ward owns the run-as-uid, mounts, and `~/.aws` passthrough; it bakes in
no user and no **target** repo.

## Naming and tags

Published to the forgejo registry as
`forgejo.coilysiren.me/coilyco-flight-deck/agentic-os`. Each release tags `vX.Y.Z`
and moves `:latest`, so a pin and its image share a version; `:buildcache` holds
the layer cache.

## How it publishes

The `publish-image` job in [`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml)
runs after a release cuts a tag, on the DinD `docker` runner: `docker login` with
the `REGISTRY_TOKEN` secret, then `buildx build --platform linux/amd64,linux/arm64
... --push` with a registry layer cache, tagging `:vX.Y.Z` and `:latest`, so each
arch pulls a native image off the cache.
`REGISTRY_TOKEN` is a `coilyco-ops` `write:package` PAT
([`rotate-registry-token.sh`](../scripts/rotate-registry-token.sh) re-mints it);
the ward build clones public source anonymously and adds no secret here.

## Pinning a tool

Versions pin as `ARG`s: hand-edit and push to main to pin or roll back, else a
scheduled **auto-bump** refreshes stale pins ([auto-bump doc](dev-base-auto-bump.md)).
`GOLANGCI_LINT_VERSION` and `KDLFMT_VERSION` opt out, bumped by hand.

## Pulling it

```bash
docker pull forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:latest
```

Needs a one-time `docker login`; `ward container up/exec` (ward#98) is the entry point.

## Not here

- Mount / compose logic and `ward container` verbs - ward#98; the mount-eligibility manifest - aos#222.
- `coily` (retired, folded into `ward ops`) and running services - not shipped.

## See also

- [release.md](release.md) - the pipeline this rides on; [FEATURES.md](FEATURES.md).

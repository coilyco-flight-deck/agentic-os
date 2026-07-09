# Tiered dev-base image design

This is the follow-up design for #377. It keeps `dev-base-full` as the default
and uses one Dockerfile with named targets to cut rebuild blast radius.

## Goals

- Keep CI and headless agents in the same declared world.
- Rebuild only the tiers a change touches.
- Keep one Dockerfile source and one release-tag family.
- Avoid per-job installs.

## Non-goals

- No Dockerfile split in this issue.
- No immediate app migration off `dev-base-full`.
- No separate version streams per image.

## Image taxonomy

- `dev-base-core` - Ubuntu, certs, shell/git, `python3`, `uv`, `pre-commit`, `ward`, minimal catalog deps.
- `dev-base-lang-node` - Node and npm.
- `dev-base-lang-go` - Go for repos that actually build or test Go in CI.
- `dev-base-lang-dotnet` - .NET SDK and ICU.
- `dev-base-ops` - `aws`, `gh`, `helm`, `kubectl`, `yq`, Docker client, Tailscale client.
- `dev-base-agent` - Claude, Codex, Goose, mcporter, self-name assets, substrate seed.
- `dev-base-full` - fan-in image for general `warded` use and the default surface.

## Dependency graph

- `core` is the root published runtime tier.
- `lang-node`, `lang-go`, `lang-dotnet`, and `ops` depend on `core`.
- `agent` depends on `core` and `lang-node`.
- `full` fans in all published functional tiers.
- A hidden builder stage may compile `ward` and other build-only binaries.
- `ward` can be built in a builder stage and copied into runtime targets, so Go does not have to live in `core`.

## Pinning model

- One repo release tag for every image class.
- Replace `docker/dev-base/ci-image-manifest.json` with a manifest of full refs.
- Downstream CI still gets a literal image ref.
- `dev-base-full` stays the default literal until ward can choose the same class.

## ARG ownership and bumping

- One canonical `ARG` defaults block.
- One ownership map for managed `ARG`s.
- One resolver per managed `ARG`.
- Tests model ownership and reachability, not copied install logic.

A tier split should not create a new source of drift.

## Release flow

- Build `dev-base-core` first.
- Build the independent tiers in parallel after core passes.
- Build `dev-base-full` only after its prerequisites pass.
- Run smoke checks per target.

The workflow can use a matrix or `buildx bake`. Target-local failures only block their dependents.

## Migration plan

1. Refactor the current Dockerfile into named targets without changing the public default.
2. Teach release CI to publish the extra image targets under the same tag.
3. Replace the single pin file with a manifest of published refs.
4. Add ward-side image class selection.
5. Move low-risk repos only after the headless lane matches.

## Follow-up slices

- #385 - split the Dockerfile into named targets and a builder stage.
- #386 - parallelize release publishing by tier.
- #387 - replace the single pinned-tag file with a manifest.
- #388 - extend `scripts/dep-bump.py` and tests with tier ownership metadata.

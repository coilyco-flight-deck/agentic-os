# CI parity: run app CI inside the release dev-base

Every app's CI runs **inside the moving `:release` [dev-base image](dev-base-image.md),
through the same `ward exec` verbs the agents run**, so a green CI means "a
headless agent can actually land this," not "it passed in some other
environment" (agentic-os#328).

The current contract follows the one promoted full dev-base image. The same
image contains every supported language toolchain.

## The motivating failure

On an app, CI was green while **every** dispatched `warded` run died. The two
environments had diverged: CI ran a bare runner + `setup-uv` (which fetches its
own writable Python, green), while the agent ran in dev-base where a root-owned
`UV_PYTHON_INSTALL_DIR` blocked `uv run` (red, invisibly). CI was validating a
world no agent lives in. Pinning CI to the same image the agents use makes those
environment regressions fail **loudly, on a PR**, before any container dispatches.

## The convention

Each app CI job runs in the dev-base container and invokes the app's own gate
verbs instead of hand-rolled `uv run` steps:

- `container: forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:release`
- `ward exec test` / `ward exec lint` / `ward exec smoke` - the same verbs a
  dispatched agent runs. Each app defines these in its own `.ward/ward.yaml`.

[`ci-in-dev-base-example.yml`](ci-in-dev-base-example.yml) is a copy-paste
starting point for an app's `.forgejo/workflows/*.yml`.

This repo's live companion is [`.forgejo/workflows/ci.yml`](../.forgejo/workflows/ci.yml).
It keeps the workflow name `ci` and the job name `gate`, so Forgejo branch
protection can require the `ci / gate` status context on `pull-request-and-merge`
repos. The live gate resolves the generated Ward tag attached to Ward's
promoted `release` branch, installs that immutable ref, then runs `pytest` plus
`pre-commit run --all-files`. If tag publication temporarily lags promotion,
the resolver falls back to the literal `release` ref.

This repo also exposes `dev-base-pr / build` only for pull requests with a
change under `docker/`. It builds the complete one-architecture Bake graph.
The job has no registry
credential and never pushes. See
[pull-request dev-base validation](pr-dev-base-build-validation.md).

## Promoted moving alias

CI uses the moving `:release` alias, never the compatibility-only `:latest`
alias. Each run consumes the newest successfully promoted full image, matching
the default used by the AOS launcher.

## The release source of truth

The release pipeline promotes the successfully published full image to
`agentic-os:release`, so consumers share one registry-owned source of truth.
[dev-base-image.md](dev-base-image.md) covers how that alias publishes.

## Authoring vs rollout

aos **authors** the convention and publishes the alias. It does not reach into
other repos. An infrastructure rollout templates the literal `:release` ref
into each app's workflow, per the authoring-vs-rollout law. The registry resolves
that alias when the app CI starts.

## Rollout unit

Each app's `.forgejo/workflows/*.yml` is the rollout unit, with a single app
as first mover on its own adoption issue. The blocking dependency was the
dev-base image fix (agentic-os#327): with it fixed, parity holds green.

## See also

- [dev-base container image](dev-base-image.md) - the image CI follows.
- [dev-base auto-bump](dev-base-auto-bump.md) - how pinned tool `ARG`s refresh.
- [pull-request dev-base validation](pr-dev-base-build-validation.md) - the build-only image gate.
- [dev-base image](dev-base-image.md) - the full image and release contract.
- [FEATURES.md](FEATURES.md) - the feature inventory this lands in.

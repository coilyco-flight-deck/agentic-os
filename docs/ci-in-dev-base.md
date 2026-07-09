# CI parity: run app CI inside the pinned dev-base

Every app's CI runs **inside the pinned [dev-base image](dev-base-image.md),
through the same `ward exec` verbs the agents run**, so a green CI means "a
headless agent can actually land this," not "it passed in some other
environment" (agentic-os#328).

The current contract still pins one `dev-base-full` image per app. The tiered
follow-up design keeps that default but introduces narrower classes behind the
same release tag and a manifest lock. See
[Tiered dev-base image design](dev-base-image-tiering.md).

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

- `container: forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:<pinned-tag>`
- `ward exec test` / `ward exec lint` / `ward exec smoke` - the same verbs a
  dispatched agent runs. Each app defines these in its own `.ward/ward.yaml`.

[`ci-in-dev-base-example.yml`](ci-in-dev-base-example.yml) is a copy-paste
starting point for an app's `.forgejo/workflows/*.yml`.

## Pinned, not `:latest`

CI pins an explicit `vX.Y.Z` tag, never `:latest`, so a run is reproducible and
adopting a newer dev-base is a **deliberate** bump - which itself re-validates
every app on the next rollout - not silent drift.

## The pinned-tag source of truth

<!-- freshness: as-of=2026-07-05 decay-class=pointer half-life=slow -->
The pin now lives in [`docker/dev-base/ci-image-manifest.json`](../docker/dev-base/ci-image-manifest.json),
owned here in aos. It maps each logical image class to a published full ref,
and every ref in the manifest carries the same release tag. [dev-base-image.md](dev-base-image.md)
covers how those tags publish.

That manifest stays the current contract. The tiered design keeps `dev-base-full`
as the default literal until ward can choose the same class directly.

## Authoring vs rollout

aos **authors** the convention and the pinned tag. It does not reach into other
repos. An ansible/template rollout in `infrastructure` **reads** the tag file
and templates it into each app's workflow as a literal `container:` tag, per the
authoring-vs-rollout law. An app CI never fetches the tag downward at run time -
it carries a rendered literal, bumped only when the rollout re-runs.

## Rollout unit

Each app's `.forgejo/workflows/*.yml` is the rollout unit; the first mover /
reference adopter is a single app, on its own adoption issue. The blocking
dependency was the dev-base image fix (agentic-os#327): with the image fixed,
ward verbs pass inside dev-base and parity holds green.

## See also

- [dev-base container image](dev-base-image.md) - the image CI pins.
- [dev-base auto-bump](dev-base-auto-bump.md) - how pinned tool `ARG`s refresh.
- [Tiered dev-base image design](dev-base-image-tiering.md) - the planned image
  family and pinning evolution.
- [FEATURES.md](FEATURES.md) - the feature inventory this lands in.

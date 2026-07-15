# PR dev-base build validation

Every pull request builds and verifies the whole dev-base image family,
without publishing anything. This shifts the validations that used to run
only on `main` left onto the PR that would break them (agentic-os#454).

## The motivating failure

In agentic-os#452, `publish-dev-base` went red **on main**: the docker build
only ran in [`release.yml`](../.forgejo/workflows/release.yml), which triggers
on push to `main`, so no PR ever exercised it. A broken Dockerfile, a stale
pinned `ARG`, or a `WARD_VERSION` / swagger-lock desync surfaced only after
merge - and a red publish also starves the fleet of a current `:latest`.

## One shared definition

The build/verify half of `publish-dev-base` is factored into the
[`actions/dev-base-build`](../actions/dev-base-build/action.yml) composite,
so the PR path and the main publish path cannot drift apart:

- `ci.yml`'s `build-dev-base` job runs it on every `pull_request` with
  `push: false` - build only.
- `release.yml`'s `publish-dev-base` runs it on `main` with `push: "true"`
  plus the registry token.

Both paths call [`scripts/dev-base-build.py`](../scripts/dev-base-build.py),
which derives the tier plan from `docker/dev-base/<tier>/Dockerfile` and
builds `core -> lang-node -> lang-go -> lang-dotnet -> ops -> agent -> full`.
Building the core tier runs the in-image `CLIGUARD_NO_SANDBOX=1 ward doctor`
gate, and the `gate` job's `pytest` run covers the
[`tests/test_dev_base_image.py`](../tests/test_dev_base_image.py)
pin-consistency checks on the same PR.

## The build-only contract

A PR run never publishes: no `--push`, no tag, no registry login, no
`REGISTRY_TOKEN` in reach. It builds the host arch through the script's local
`docker build` path (the same path `ward exec dev-base-build` uses), tags each
tier `pr-<run_id>`, and drops those tags again in a cleanup step. Image
layers stay on the shared daemon as build cache, so later PR builds are warm.
Publish, the release tag, and the GitHub mirror stay main-only.

`gate` additionally dry-runs the release tag computation through
[`actions/tag-bump`](../actions/tag-bump/action.yml) with `create_tag: false`,
so a broken release-planning change also fails pre-merge. The scheduled
workflows (`dep-bump.yml`, `freshness.yml`) and the deploy-shaped
`mirror-to-github.yml` stay off PRs by design.

## Required status check

Branch protection on `pull-requests-and-merge` repos should require the
`ci / build-dev-base` context alongside `ci / gate`, so a red image build
blocks the merge instead of landing and going red on `main`.

## See also

- [ci-in-dev-base.md](ci-in-dev-base.md) - the PR gate convention this extends.
- [dev-base-image.md](dev-base-image.md) - what the image family ships.
- [release.md](release.md) - the main-only publish half.

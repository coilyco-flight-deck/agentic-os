# Pull-request dev-base build validation

Every pull request exposes the `ci / build-dev-base` status context. The job
builds only the affected dev-base image closure for one local architecture. It
never logs in to the registry and never pushes an image.

## Affected image plan

[`agentic_os/dev_base.py`](../agentic_os/dev_base.py) is the canonical tier
specification. It owns the five independent language images, the full image,
and the full image's Rust base plus Go, .NET, and Python grafts.

The validation action diffs the pull request from its base revision and asks
[`scripts/dev-base-build.py`](../scripts/dev-base-build.py) for two sets:

* **affected tiers** - tiers whose Dockerfile, context, named context, or build
  definition changed, plus downstream compositions
* **build tiers** - the affected tiers plus every source image needed to build
  them locally

A common installer, shared language Dockerfile, named AOS context, or build
definition affects every language image and the full composition. A full-only
change builds the Rust base and three graft sources before full. A pull request
with no dev-base input change keeps the status context but skips Docker setup.

## Build-only boundary

[`actions/dev-base-build`](../actions/dev-base-build/action.yml) has no registry
token input. It installs the same uv, Docker, and Buildx versions as
publication, then uses Buildx Bake target links for one platform. Specialist
results remain in BuildKit's cache-only exporter and feed the `full` target
directly. Only `full` is loaded into the runner's Docker store for the shared
smoke check. The action does not install QEMU, does not pass `--push`, and
removes the run's local tags afterward.

The persistent `aos-pr-builder` cache is pruned to its configured maximum after
every run. PR validation therefore reuses warm layers without allowing the
shared runner cache to grow without a bound.

## Publication parity

PR validation and
[`actions/publish-dev-base`](../actions/publish-dev-base/action.yml) share:

* [`scripts/dev-base-build.py`](../scripts/dev-base-build.py), including tier
  order, Dockerfiles, named contexts, build arguments, and image tags
* the uv, Docker, daemon-resolution, and builder setup scripts under
  [`actions/publish-dev-base/scripts`](../actions/publish-dev-base/scripts)
* [`verify-full.sh`](../actions/publish-dev-base/scripts/verify-full.sh), with
  one PR platform or both published platforms

Every built language target runs
[`verify-common.sh`](../docker/dev-base/verify-common.sh) inside its Dockerfile.
That gate includes `WARD_DOCTOR_ALLOW_PLACEHOLDERS=1 ward doctor`. The full
image then runs the shared complete-toolchain smoke.

Publication keeps its registry login, per-tier registry cache, and
multi-architecture push. None of those write surfaces are inputs to the PR
action.

## Required status

After the workflow is stable, branch protection should require
`ci / build-dev-base` alongside `ci / gate`. The protected context makes a
broken language image, common installer, build plan, or full graft fail on its
own pull request.

## See also

* [dev-base image family](dev-base-image.md)
* [dev-base build cache](dev-base-build-cache.md)
* [CI parity](ci-in-dev-base.md)
* [release pipeline](release.md)

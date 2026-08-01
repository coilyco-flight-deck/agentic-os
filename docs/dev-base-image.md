# dev-base image family

AOS publishes five language-specialist images and one full compatibility image.
Every specialist starts directly from `ubuntu:24.04`. `agentic-os:${TAG}` is
the full surface, and `agentic-os:release` remains the moving default used by
the AOS launcher and CI.

## What ships

[`docker/dev-base/Dockerfile`](../docker/dev-base/Dockerfile) owns the five
independent language targets. Each target runs the same
[`install-common.sh`](../docker/dev-base/install-common.sh) source and adds one
toolchain:

* `lang-node`
* `lang-go`
* `lang-dotnet`
* `lang-rust`
* `lang-python`

Every image carries Node because the common agent harnesses require it. The
specialist name identifies the additional development toolchain.

The common surface also carries a release-pinned `aos`, Ward for fixed workflow orchestration,
`aosguard` for operator commands, agent-compose with its embedded `person:kai`
source, and the repository's packaged aosguard Python bridges. Each image build renders
aosguard's native agent skill, renders an agent-compose roster, and checks the
generated person snapshot plus personality definitions. Linuxbrew is not part
of any image.

The common surface includes `kubectl`, but image builds own no host mounts,
kubeconfig, or cluster transport. The standalone AOS launcher may add an
[operator-selected kubeconfig](aos-kubeconfig.md) for an authorized role.
Language images remain artifacts with no host-specific mount logic.

[`docker/dev-base/full/Dockerfile`](../docker/dev-base/full/Dockerfile) starts
from the same-release Rust image and grafts Go, .NET, and Python tooling from
their same-release images. Node is already present in the common surface. The
full-only gate tools are `golangci-lint`, `trufflehog`, and `kdlfmt`.

## Build and publication

`ward exec dev-base-build` executes the declarative
[`docker-bake.hcl`](../docker/dev-base/docker-bake.hcl), building all five local
specialists and then `agentic-os:dev-base-local`. The Dockerfile downloads the
checksummed AOS binary named by `AOS_VERSION`. AOSguard spec, Python bridges,
and repository manifests remain named build contexts.

[`dev-base-publish.yml`](../.forgejo/workflows/dev-base-publish.yml) skips
unless the promoted diff changes a path under `docker/`, then builds every
specialist in a Forgejo matrix and the full fan-in image through `needs`. Manual dispatch overrides the filter.
[`release.yml`](../.forgejo/workflows/release.yml) promotes every manifest to
its versioned and moving tags. Language tags use
`lang-<language>-<tag>`. The full image keeps the plain `<tag>`, `release`, and
`latest` names. Both paths check each target manifest before work, so a retry
skips an image that already landed. See [publish resume](dev-base-publish-resume.md).

Pull requests with a `docker/` change run the complete source graph through
[`actions/dev-base-build`](../actions/dev-base-build/action.yml). PR validation and publication
share the Docker definitions and verification. PR builds have no registry credential. See
[PR build validation](pr-dev-base-build-validation.md).

## Pinning a tool

Every managed version has one default `ARG` across the two Dockerfiles.
`ward exec dep-bump -- check` compares those pins with upstream releases.
`ward exec dep-bump -- apply --arg NAME --version VERSION` rewrites one owning
declaration.

Source ownership follows the tool boundary. The image owns this deployment's
Git identity and its entrypoint maps that identity onto Ward's provider-neutral
`WARD_GIT_*` environment contract before container bootstrap. The image does
not redefine Ward policy, aosguard policy, or agent-compose source data.

## See also

* [CI parity](ci-in-dev-base.md)
* [Build cache](dev-base-build-cache.md)
* [PR build validation](pr-dev-base-build-validation.md)
* [Release workflow](release.md)

# dev-base container image

AOS publishes one development image. `agentic-os:${TAG}` is the full surface,
and `agentic-os:release` is the moving default used by the AOS launcher and CI.
There are no language-specialist, core, ops, or agent image tags.

## What ships

[`docker/dev-base/Dockerfile`](../docker/dev-base/Dockerfile) owns the single
`dev-base-full` target. It installs the common agent surface once, then adds
every supported language toolchain:

* Node and the JavaScript agent tools
* Go
* .NET and ICU
* Rust, wasm, `trunk`, and native Bevy/Winit development libraries
* Python, pip, and `pipenv`

The image also carries `aos`, Ward for role-scoped orchestration, `aosguard` for
operator commands, agent-compose with its embedded `person:kai` source, and the
repository's packaged aosguard Python bridges. The image build renders
aosguard's native agent skill, renders an agent-compose roster, and checks the
generated person snapshot plus personality definitions. Full-only gate tools
include `golangci-lint`, `trufflehog`, and `kdlfmt`.

## Build and publication

`ward exec dev-base-build` builds `agentic-os:dev-base-local`.
[`scripts/dev-base-build.py`](../scripts/dev-base-build.py) supplies the AOS
CLI, aosguard spec, and aosguard Python package as named Docker contexts.

[`dev-base-publish.yml`](../.forgejo/workflows/dev-base-publish.yml) builds one
multi-architecture draft manifest after the release branch advances.
[`release.yml`](../.forgejo/workflows/release.yml) promotes that manifest to the
versioned tag plus `release` and `latest`. Both paths check the target manifest
before work, so a retry skips an image that already landed. See
[publish resume](dev-base-publish-resume.md).

## Pinning a tool

Every managed version has one default `ARG` in the Dockerfile.
`ward exec dep-bump -- check` compares those pins with upstream releases.
`ward exec dep-bump -- apply --arg NAME --version VERSION` rewrites one owning
declaration.

Source ownership follows the tool boundary. The image pins versions but does
not redefine Ward configuration, aosguard policy, or agent-compose source data.

## See also

* [CI parity](ci-in-dev-base.md)
* [Build cache](dev-base-build-cache.md)
* [Release workflow](release.md)

# Tiered dev-base image split

This is the implemented tier split for dev-base. The old monolithic Dockerfile
became one folder per published tier, each with a literal `Dockerfile`, while
`dev-base-full` kept the default `:latest` surface.

## Tier layout

- `docker/dev-base/core/Dockerfile` - Ubuntu, certs, shell/git, `python3`, `uv`, `pre-commit`, `ward`, Rust, and the hidden `dev-base-ward-builder` stage that compiles `ward`.
- `docker/dev-base/lang-node/Dockerfile` - Node and npm.
- `docker/dev-base/lang-go/Dockerfile` - Go for repos that build or test Go in CI.
- `docker/dev-base/lang-dotnet/Dockerfile` - .NET SDK and ICU.
- `docker/dev-base/ops/Dockerfile` - `aws`, `gh`, `helm`, `kubectl`, `yq`, Docker client, Tailscale client.
- `docker/dev-base/agent/Dockerfile` - Claude, Codex, Goose, mcporter, self-name assets, substrate seed.
- `docker/dev-base/full/Dockerfile` - fan-in image for general `warded` use and the default surface.

## Dependency graph

- `core` is the root published runtime tier.
- `lang-node`, `lang-go`, `lang-dotnet`, and `ops` build from the previous tier image.
- `agent` builds from `ops`.
- `full` builds last from `agent`.
- The hidden builder stage stays inside `core` so the ward binary still compiles per target platform during the core build.

## Tag derivation

- One repo release tag drives the whole family.
- The folder name becomes the image suffix, so `core` becomes `agentic-os-core:${TAG}` and `full` becomes `agentic-os-full:${TAG}`.
- The release helper in [`scripts/dev-base-build.py`](../scripts/dev-base-build.py) derives the plan from the directory layout.
- There is no checked-in `docker/dev-base/ci-image-manifest.json` anymore. Every published ref is derivable from `{registry base, folder name, tag}`, so the JSON map would only duplicate the folder layout.

## Release flow

- `release.yml` computes the next tag first.
- It then calls the helper with `--push`, which builds and verifies each tier in order.
- Every pushed tier carries the moving `:latest` alias alongside the release tag, so `dev-base-full` still fans in last and keeps the default `agentic-os-full:latest` surface ward pulls.

## ARG ownership

- `UV_VERSION` and `WARD_VERSION` live in `core`.
- `NODE_VERSION` lives in `lang-node`.
- `GO_VERSION` lives in `lang-go`.
- `DOTNET_VERSION` lives in `lang-dotnet`.
- `AWSCLI_VERSION`, `GH_VERSION`, `DOCKER_VERSION`, `HELM_VERSION`, `KUBECTL_VERSION`, `YQ_VERSION`, and `TAILSCALE_VERSION` live in `ops`.
- `CLAUDE_VERSION`, `MCPORTER_VERSION`, `OPENCODE_VERSION`, `CODEX_VERSION`, and `GOOSE_VERSION` live in `agent`.
- `GOLANGCI_LINT_VERSION`, `TRUFFLEHOG_VERSION`, and `KDLFMT_VERSION` live in `full`.

## See also

- [dev-base container image](dev-base-image.md) - the current published contract.
- [CI parity in dev-base](ci-in-dev-base.md) - the pinned consumer side.
- [FEATURES.md](FEATURES.md) - the feature inventory this lands in.

# Canonical agent dev environment, published per release as the dev-base image. See docs/dev-base-image.md.
FROM ubuntu:24.04

# Pinned toolchain. Auto-bumped against upstream by .forgejo/workflows/dep-bump.yml
# (one commit per tool); edit an ARG by hand to pin or roll back. See docs/dev-base-image.md.
ARG UV_VERSION=0.11.21
ARG NODE_VERSION=22.22.3
ARG GO_VERSION=1.26.4
ARG AWSCLI_VERSION=2.35.5
ARG CLAUDE_VERSION=2.1.187
ARG CODEX_VERSION=0.141.0
ARG GOOSE_VERSION=1.38.0
ARG DOCKER_VERSION=28.5.1

# buildx populates TARGETARCH (amd64|arm64) per platform in the manifest list.
ARG TARGETARCH

# uv tools land on the global PATH so any run-as-uid finds pre-commit.
ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin \
    UV_TOOL_DIR=/opt/uv/tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python

# Base packages: catalog-hook deps (shellcheck, python3, git) plus the inner loop's fetch/build tools.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl wget git gnupg jq ripgrep less unzip xz-utils socat \
      build-essential openssh-client procps shellcheck \
      python3 python3-pip python3-venv \
 && rm -rf /var/lib/apt/lists/*

# Map Docker's TARGETARCH onto each upstream's arch spelling once.
RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) NODE_ARCH=x64;   GO_ARCH=amd64; AWS_ARCH=x86_64; CODEX_ARCH=x86_64; GOOSE_ARCH=x86_64; DOCKER_ARCH=x86_64 ;; \
      arm64) NODE_ARCH=arm64; GO_ARCH=arm64; AWS_ARCH=aarch64; CODEX_ARCH=aarch64; GOOSE_ARCH=aarch64; DOCKER_ARCH=aarch64 ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    echo "NODE_ARCH=${NODE_ARCH} GO_ARCH=${GO_ARCH} AWS_ARCH=${AWS_ARCH} CODEX_ARCH=${CODEX_ARCH} GOOSE_ARCH=${GOOSE_ARCH} DOCKER_ARCH=${DOCKER_ARCH}" > /tmp/arch.env

# uv (Python project + tool manager).
RUN set -eux; \
    curl -fsSL "https://astral.sh/uv/${UV_VERSION}/install.sh" \
      | env INSTALLER_NO_MODIFY_PATH=1 UV_INSTALL_DIR=/usr/local/bin sh; \
    uv --version

# pre-commit, as a uv tool on the global bin dir.
RUN set -eux; \
    uv tool install "pre-commit"; \
    chmod -R a+rX /opt/uv; \
    pre-commit --version

# Node + npm (Claude Code's runtime).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" \
      -o /tmp/node.tar.xz; \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
      --exclude='*/CHANGELOG.md' --exclude='*/README.md' --exclude='*/LICENSE'; \
    rm /tmp/node.tar.xz; \
    node --version; npm --version

# Go (builds the warp module's pre-commit hooks and, later, ward).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz" \
      -o /tmp/go.tar.gz; \
    tar -xzf /tmp/go.tar.gz -C /usr/local; \
    rm /tmp/go.tar.gz; \
    go version

# AWS CLI v2 (SSM secret loader + ~/.aws passthrough).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_ARCH}-${AWSCLI_VERSION}.zip" \
      -o /tmp/awscli.zip; \
    unzip -q /tmp/awscli.zip -d /tmp; \
    /tmp/aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli; \
    rm -rf /tmp/awscli.zip /tmp/aws; \
    aws --version

# Claude Code, pinned.
RUN set -eux; \
    npm install -g "@anthropic-ai/claude-code@${CLAUDE_VERSION}"; \
    claude --version

# Codex CLI, pinned. ward injects host ~/.codex/auth.json at container launch.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://github.com/openai/codex/releases/download/rust-v${CODEX_VERSION}/codex-${CODEX_ARCH}-unknown-linux-musl.tar.gz" \
      -o /tmp/codex.tar.gz; \
    tar -xzf /tmp/codex.tar.gz -C /usr/local/bin; \
    mv "/usr/local/bin/codex-${CODEX_ARCH}-unknown-linux-musl" /usr/local/bin/codex; \
    chmod 0755 /usr/local/bin/codex; \
    rm /tmp/codex.tar.gz; \
    codex --version

# Goose CLI (block/goose), pinned. Statically linked musl build, no runtime deps.
# Unblocks the `ward agent goose work|headless|task|reply` surface the ward
# entrypoint already wires (it dropped to a shell while the binary was absent).
# goose floats over a model provider it reads from ~/.config/goose; wiring that
# into the container is ward's concern (the adapter manifest's goose `auth` slot).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://github.com/block/goose/releases/download/v${GOOSE_VERSION}/goose-${GOOSE_ARCH}-unknown-linux-musl.tar.gz" \
      -o /tmp/goose.tar.gz; \
    tar -xzf /tmp/goose.tar.gz -C /usr/local/bin ./goose; \
    chmod 0755 /usr/local/bin/goose; \
    rm /tmp/goose.tar.gz; \
    goose --version

# Docker CLI (client only, no daemon). ward's read-only `explore` session binds the
# host docker socket so the in-container agent can dispatch a sibling `warded #N`
# headless run; that needs a `docker` client in the image (ward#315). The static
# tarball ships the full engine - extract only the client binary.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${DOCKER_ARCH}/docker-${DOCKER_VERSION}.tgz" \
      -o /tmp/docker.tgz; \
    tar -xzf /tmp/docker.tgz -C /usr/local/bin --strip-components=1 docker/docker; \
    chmod 0755 /usr/local/bin/docker; \
    rm /tmp/docker.tgz; \
    docker --version

# Agent self-name (agentic-os#281). Warded explorers / headless agents run in
# this image and otherwise get no name - host sessions self-name via a Claude
# Code SessionStart + statusLine hook the claude-hooks ansible role wires into
# ~/.claude/settings.json, but that role never runs in a container. Bake the
# slice in instead: the trimmed agent-name.sh under /opt (world-readable, so it
# runs as any uid like every other tool here) plus a policy-tier
# managed-settings.json at the fixed /etc/claude-code path. Policy settings are
# the one Claude Code surface whose location does not depend on the run-as-uid,
# HOME, or CLAUDE_CONFIG_DIR ward picks - exactly right for an image that bakes
# in no user. It only adds statusLine + the SessionStart self-name hook, so it
# layers cleanly over whatever ward injects into user settings. See
# docs/dev-base-self-name.md.
COPY agent-name.sh /opt/agentic-os/agent-name.sh
COPY claude-managed-settings.json /etc/claude-code/managed-settings.json
RUN set -eux; \
    chmod 0755 /opt/agentic-os/agent-name.sh; \
    chmod 0644 /etc/claude-code/managed-settings.json

# Substrate seed: bare mirrors of the public (image-tier) reference repos a ward
# container warms its gitcache from on a cold volume. List is a denormalized copy
# of the image-tier subset of ward's cmd/ward/containerassets/preclone-repos.txt.
# All public read (anonymous clone). Bridge/private repos are deliberately not
# baked into this shareable image. Mirror dir name matches ward's owner__name.git.
COPY substrate-image-repos.txt /tmp/substrate-image-repos.txt
RUN set -eux; \
    mkdir -p /opt/substrate-seed; \
    while read -r ref; do \
      case "$ref" in ''|\#*) continue ;; esac; \
      owner="${ref%%/*}"; name="${ref##*/}"; \
      case "$owner" in \
        coilysiren) base="https://github.com" ;; \
        *) base="https://forgejo.coilysiren.me" ;; \
      esac; \
      git clone --mirror "$base/$owner/$name.git" "/opt/substrate-seed/${owner}__${name}.git"; \
    done < /tmp/substrate-image-repos.txt; \
    rm /tmp/substrate-image-repos.txt; \
    chmod -R a+rX /opt/substrate-seed

WORKDIR /workspace
CMD ["bash"]

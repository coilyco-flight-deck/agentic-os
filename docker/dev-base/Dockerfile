# syntax=docker/dockerfile:1
# Language targets are build-only payloads. Forgejo builds them in parallel,
# keeps stable registry caches across runs, and feeds their commit-scoped draft
# manifests into the one released full image.

ARG UV_VERSION=0.12.0
ARG GO_VERSION=1.26.5
ARG DOTNET_VERSION=10.0.302
ARG TRUNK_VERSION=0.21.14
ARG NODE_VERSION=22.23.2

FROM ubuntu:24.04 AS dev-base-lang-node
ARG NODE_VERSION
ARG TARGETARCH
ENV PATH=/usr/local/node/bin:/usr/local/bin:/usr/bin:/bin
LABEL org.opencontainers.image.source="https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="agentic-os Node build payload"
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN --mount=type=bind,source=write-arch-env.sh,target=/tmp/write-arch-env.sh \
    TARGETARCH="${TARGETARCH}" bash /tmp/write-arch-env.sh
RUN set -eux; . /opt/agentic-os/arch.env; \
    apt-get update; apt-get install -y --no-install-recommends ca-certificates curl xz-utils; \
    rm -rf /var/lib/apt/lists/*; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" \
      -o /tmp/node.tar.xz; \
    install -d /usr/local/node; \
    tar -xJf /tmp/node.tar.xz -C /usr/local/node --strip-components=1 \
      --exclude='*/CHANGELOG.md' --exclude='*/README.md' --exclude='*/LICENSE'; \
    rm /tmp/node.tar.xz; node --version; npm --version

FROM ubuntu:24.04 AS dev-base-lang-go
ARG GO_VERSION
ARG TARGETARCH
ENV PATH=/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin
LABEL org.opencontainers.image.source="https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="agentic-os Go build payload"
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN --mount=type=bind,source=write-arch-env.sh,target=/tmp/write-arch-env.sh \
    TARGETARCH="${TARGETARCH}" bash /tmp/write-arch-env.sh
RUN set -eux; . /opt/agentic-os/arch.env; \
    apt-get update; apt-get install -y --no-install-recommends ca-certificates curl; \
    rm -rf /var/lib/apt/lists/*; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      "https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz" -o /tmp/go.tar.gz; \
    tar -xzf /tmp/go.tar.gz -C /usr/local; rm /tmp/go.tar.gz; go version

FROM ubuntu:24.04 AS dev-base-lang-dotnet
ARG DOTNET_VERSION
ARG TARGETARCH
ENV PATH=/usr/local/dotnet:/usr/local/bin:/usr/bin:/bin \
    DOTNET_ROOT=/usr/local/dotnet DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
LABEL org.opencontainers.image.source="https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="agentic-os .NET build payload"
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN --mount=type=bind,source=write-arch-env.sh,target=/tmp/write-arch-env.sh \
    TARGETARCH="${TARGETARCH}" bash /tmp/write-arch-env.sh
RUN set -eux; . /opt/agentic-os/arch.env; \
    apt-get update; apt-get install -y --no-install-recommends ca-certificates curl; \
    rm -rf /var/lib/apt/lists/*; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh; \
    chmod 0755 /tmp/dotnet-install.sh; \
    /tmp/dotnet-install.sh --version "${DOTNET_VERSION}" --architecture "${DOTNET_ARCH}" \
      --install-dir /usr/local/dotnet --no-path; \
    rm /tmp/dotnet-install.sh; chmod -R a+rX /usr/local/dotnet; dotnet --list-sdks

FROM ubuntu:24.04 AS dev-base-lang-rust
ARG TRUNK_VERSION
ARG TARGETARCH
ENV PATH=/usr/local/cargo/bin:/usr/local/bin:/usr/bin:/bin \
    CARGO_HOME=/usr/local/cargo RUSTUP_HOME=/usr/local/rustup
LABEL org.opencontainers.image.source="https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="agentic-os Rust build payload"
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN --mount=type=bind,source=write-arch-env.sh,target=/tmp/write-arch-env.sh \
    TARGETARCH="${TARGETARCH}" bash /tmp/write-arch-env.sh
RUN set -eux; apt-get update; apt-get install -y --no-install-recommends \
      build-essential ca-certificates curl libasound2-dev libudev-dev \
      libwayland-dev libxkbcommon-dev pkg-config; \
    rm -rf /var/lib/apt/lists/*; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      https://sh.rustup.rs -o /tmp/rustup-init.sh; chmod 0755 /tmp/rustup-init.sh; \
    /tmp/rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain stable; \
    rm /tmp/rustup-init.sh; rustup target add wasm32-unknown-unknown; \
    chmod -R a+rwX /usr/local/cargo /usr/local/rustup; cargo --version
RUN set -eux; . /opt/agentic-os/arch.env; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      "https://github.com/trunk-rs/trunk/releases/download/v${TRUNK_VERSION}/trunk-${KDL_ARCH}-unknown-linux-gnu.tar.gz" \
      -o /tmp/trunk.tar.gz; \
    tar -xzf /tmp/trunk.tar.gz -C /usr/local/cargo/bin trunk; \
    chmod 0755 /usr/local/cargo/bin/trunk; rm /tmp/trunk.tar.gz; trunk --version
RUN printf '%s\n' '#include <wayland-client.h>' '#include <xkbcommon/xkbcommon.h>' \
      'int main(void) { return 0; }' > /tmp/rust-native-smoke.c; \
    cc /tmp/rust-native-smoke.c $(pkg-config --cflags --libs wayland-client xkbcommon) \
      -o /tmp/rust-native-smoke; /tmp/rust-native-smoke; \
    rm /tmp/rust-native-smoke /tmp/rust-native-smoke.c

FROM ubuntu:24.04 AS dev-base-lang-python
ARG UV_VERSION
ARG TARGETARCH
ENV PATH=/usr/local/bin:/usr/bin:/bin \
    UV_TOOL_DIR=/opt/uv/tools UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python
LABEL org.opencontainers.image.source="https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="agentic-os Python build payload"
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN --mount=type=bind,source=write-arch-env.sh,target=/tmp/write-arch-env.sh \
    TARGETARCH="${TARGETARCH}" bash /tmp/write-arch-env.sh
RUN set -eux; apt-get update; apt-get install -y --no-install-recommends \
      ca-certificates curl python3 python3-pip python3-venv; \
    rm -rf /var/lib/apt/lists/*; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      "https://astral.sh/uv/${UV_VERSION}/install.sh" \
      | env INSTALLER_NO_MODIFY_PATH=1 UV_INSTALL_DIR=/usr/local/bin sh; \
    uv tool install pipenv; uv python install 3.13 3.12; \
    chmod -R a+rwX /opt/uv; uv --version; pipenv --version; uv python list

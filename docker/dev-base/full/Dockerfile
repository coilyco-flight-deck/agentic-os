# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ubuntu:24.04
ARG LANG_GO_IMAGE=${BASE_IMAGE}
ARG LANG_DOTNET_IMAGE=${BASE_IMAGE}
ARG LANG_PYTHON_IMAGE=${BASE_IMAGE}
FROM ${LANG_GO_IMAGE} AS dev-base-lang-go-graft
FROM ${LANG_DOTNET_IMAGE} AS dev-base-lang-dotnet-graft
FROM ${LANG_PYTHON_IMAGE} AS dev-base-lang-python-graft
FROM ${BASE_IMAGE} AS dev-base-full
ARG GOLANGCI_LINT_VERSION=2.12.2
ARG TRUFFLEHOG_VERSION=3.95.8
ARG KDLFMT_VERSION=0.1.7

LABEL org.opencontainers.image.source="https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="agentic-os full"
ENV PATH=/usr/local/go/bin:/usr/local/dotnet:/usr/local/node/bin:/usr/local/cargo/bin:/usr/local/bin:/usr/bin:/bin \
    DOTNET_ROOT=/usr/local/dotnet \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY --from=dev-base-lang-go-graft /usr/local/go /usr/local/go
COPY --from=dev-base-lang-dotnet-graft /usr/local/dotnet /usr/local/dotnet
COPY --from=dev-base-lang-python-graft /opt/uv/tools/pipenv /opt/uv/tools/pipenv
COPY --from=dev-base-lang-python-graft /usr/local/bin/python /usr/local/bin/python
COPY --from=dev-base-lang-python-graft /usr/local/bin/pip /usr/local/bin/pip
COPY --from=dev-base-lang-python-graft /usr/local/bin/pipenv /usr/local/bin/pipenv

RUN set -eux; . /opt/agentic-os/arch.env; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      "https://github.com/golangci/golangci-lint/releases/download/v${GOLANGCI_LINT_VERSION}/golangci-lint-${GOLANGCI_LINT_VERSION}-linux-${GOLANGCI_ARCH}.tar.gz" \
      -o /tmp/golangci-lint.tar.gz; \
    tar -xzf /tmp/golangci-lint.tar.gz -C /usr/local/bin --strip-components=1 \
      "golangci-lint-${GOLANGCI_LINT_VERSION}-linux-${GOLANGCI_ARCH}/golangci-lint"; \
    chmod 0755 /usr/local/bin/golangci-lint; \
    rm /tmp/golangci-lint.tar.gz; golangci-lint --version
RUN set -eux; . /opt/agentic-os/arch.env; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      "https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_${TRUFFLEHOG_ARCH}.tar.gz" \
      -o /tmp/trufflehog.tar.gz; \
    tar -xzf /tmp/trufflehog.tar.gz -C /usr/local/bin trufflehog; \
    chmod 0755 /usr/local/bin/trufflehog; \
    rm /tmp/trufflehog.tar.gz; trufflehog --version
RUN set -eux; . /opt/agentic-os/arch.env; \
    curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
      "https://github.com/hougesen/kdlfmt/releases/download/v${KDLFMT_VERSION}/kdlfmt-${KDL_ARCH}-unknown-linux-gnu.tar.xz" \
      -o /tmp/kdlfmt.tar.xz; \
    tar -xJf /tmp/kdlfmt.tar.xz -C /usr/local/bin --strip-components=1 \
      "kdlfmt-${KDL_ARCH}-unknown-linux-gnu/kdlfmt"; \
    chmod 0755 /usr/local/bin/kdlfmt; \
    rm /tmp/kdlfmt.tar.xz; kdlfmt --version

RUN node --version && go version && dotnet --list-sdks && cargo --version && \
    trunk --version && python --version && pipenv --version && aosguard --version
WORKDIR /workspace
ENTRYPOINT ["/opt/agentic-os/ward-shell-entrypoint.sh"]
CMD ["bash"]

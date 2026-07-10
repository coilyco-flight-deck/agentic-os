ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS dev-base-lang-go
ARG GO_VERSION=1.26.5

# Go (builds the warp module's pre-commit hooks and, later, ward).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz" \
      -o /tmp/go.tar.gz; \
    tar -xzf /tmp/go.tar.gz -C /usr/local; \
    rm /tmp/go.tar.gz; \
    go version

ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS dev-base-full
ARG GOLANGCI_LINT_VERSION
ARG TRUFFLEHOG_VERSION
ARG KDLFMT_VERSION

# golangci-lint (Go linter for ward + cli-guard). Closes the missing-binary gap
# that made the in-container `pre-commit run --all-files` / CI lint job unrunnable
# for agents. Release tag is v-prefixed; the tarball name and its
# top-level dir are not. Pinned to the consuming repos' CI version (see the ARG).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v${GOLANGCI_LINT_VERSION}/golangci-lint-${GOLANGCI_LINT_VERSION}-linux-${GOLANGCI_ARCH}.tar.gz" \
      -o /tmp/golangci-lint.tar.gz; \
    tar -xzf /tmp/golangci-lint.tar.gz -C /usr/local/bin --strip-components=1 \
      "golangci-lint-${GOLANGCI_LINT_VERSION}-linux-${GOLANGCI_ARCH}/golangci-lint"; \
    chmod 0755 /usr/local/bin/golangci-lint; \
    rm /tmp/golangci-lint.tar.gz; \
    golangci-lint --version

# trufflehog (secret scanner for the catalog suite's offline trufflehog hook).
# The static Go binary sits at the tarball root; extract just it.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_${TRUFFLEHOG_ARCH}.tar.gz" \
      -o /tmp/trufflehog.tar.gz; \
    tar -xzf /tmp/trufflehog.tar.gz -C /usr/local/bin trufflehog; \
    chmod 0755 /usr/local/bin/trufflehog; \
    rm /tmp/trufflehog.tar.gz; \
    trufflehog --version

# kdlfmt (KDL formatter for ward-kdl guardfiles, via ward's language:system hook).
# cargo-dist ships a .tar.xz with the binary under a target-triple dir; only the
# gnu build covers both arches (no aarch64 musl), and ubuntu's glibc runs it.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://github.com/hougesen/kdlfmt/releases/download/v${KDLFMT_VERSION}/kdlfmt-${KDL_ARCH}-unknown-linux-gnu.tar.xz" \
      -o /tmp/kdlfmt.tar.xz; \
    tar -xJf /tmp/kdlfmt.tar.xz -C /usr/local/bin --strip-components=1 \
      "kdlfmt-${KDL_ARCH}-unknown-linux-gnu/kdlfmt"; \
    chmod 0755 /usr/local/bin/kdlfmt; \
    rm /tmp/kdlfmt.tar.xz; \
    kdlfmt --version

WORKDIR /workspace
CMD ["bash"]

ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS dev-base-lang-rust
ARG TRUNK_VERSION=0.21.14

# Rust toolchain in the self-contained /usr/local/cargo + /usr/local/rustup
# prefixes core's ENV already points at, so full grafts them via COPY --from.
RUN set -eux; \
    curl -fsSL https://sh.rustup.rs -o /tmp/rustup-init.sh; \
    chmod 0755 /tmp/rustup-init.sh; \
    /tmp/rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain stable; \
    rm /tmp/rustup-init.sh; \
    rustup target add wasm32-unknown-unknown; \
    rustup --version; \
    cargo --version; \
    rustc --version

# trunk (static-site Wasm packager) lands in cargo/bin so the graft carries
# it. Release triple spelling matches KDL_ARCH (x86_64/aarch64).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://github.com/trunk-rs/trunk/releases/download/v${TRUNK_VERSION}/trunk-${KDL_ARCH}-unknown-linux-gnu.tar.gz" \
      -o /tmp/trunk.tar.gz; \
    tar -xzf /tmp/trunk.tar.gz -C /usr/local/cargo/bin trunk; \
    chmod 0755 /usr/local/cargo/bin/trunk; \
    rm /tmp/trunk.tar.gz; \
    trunk --version; \
    chmod -R a+rwX /usr/local/cargo /usr/local/rustup

WORKDIR /workspace
CMD ["bash"]

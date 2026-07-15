ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS dev-base-lang-node
ARG NODE_VERSION=22.23.1

# Node + npm (Claude Code's runtime). The whole toolchain lives under the
# self-contained /usr/local/node prefix (core's ENV already puts its bin on
# PATH) so the agent tier can graft it with a single COPY --from instead of
# inheriting it through a linear tier chain (aos#491). npm's global prefix
# follows the node binary, so `npm install -g` in downstream tiers lands
# inside the same grafted directory.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" \
      -o /tmp/node.tar.xz; \
    mkdir -p /usr/local/node; \
    tar -xJf /tmp/node.tar.xz -C /usr/local/node --strip-components=1 \
      --exclude='*/CHANGELOG.md' --exclude='*/README.md' --exclude='*/LICENSE'; \
    rm /tmp/node.tar.xz; \
    node --version; npm --version

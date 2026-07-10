ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS dev-base-ops
ARG AWSCLI_VERSION=2.35.15
ARG GH_VERSION=2.96.0
ARG DOCKER_VERSION=28.5.2
ARG HELM_VERSION=4.2.2
ARG KUBECTL_VERSION=1.36.2
ARG YQ_VERSION=4.53.3
ARG TAILSCALE_VERSION=1.98.8

# AWS CLI v2 (SSM secret loader + ~/.aws passthrough).
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_ARCH}-${AWSCLI_VERSION}.zip" \
      -o /tmp/awscli.zip; \
    unzip -q /tmp/awscli.zip -d /tmp; \
    /tmp/aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli; \
    rm -rf /tmp/awscli.zip /tmp/aws; \
    aws --version

# Fleet CI utilities that are generic enough to live in the shared base.
# buildx stays job-local because the publish-image workflow still bootstraps a
# privileged Docker daemon stack there. Rust ships here as the shared workspace
# baseline now, while wasm-pack stays job-local because it is a heavier,
# repo-specific toolchain rather than a recurring shared CLI.
#
# gh, helm, kubectl, and yq are pinned here so downstream workflows can drop
# their package-manager/setup-action installs after the next image publish.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz" \
      -o /tmp/gh.tar.gz; \
    tar -xzf /tmp/gh.tar.gz -C /usr/local/bin --strip-components=2 \
      "gh_${GH_VERSION}_linux_${GH_ARCH}/bin/gh"; \
    chmod 0755 /usr/local/bin/gh; \
    rm /tmp/gh.tar.gz; \
    gh --version; \
    curl -fsSL "https://get.helm.sh/helm-v${HELM_VERSION}-linux-${HELM_ARCH}.tar.gz" \
      -o /tmp/helm.tar.gz; \
    tar -xzf /tmp/helm.tar.gz -C /usr/local/bin --strip-components=1 \
      "linux-${HELM_ARCH}/helm"; \
    chmod 0755 /usr/local/bin/helm; \
    rm /tmp/helm.tar.gz; \
    helm version --short; \
    curl -fsSL "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/${KUBECTL_ARCH}/kubectl" \
      -o /usr/local/bin/kubectl; \
    chmod 0755 /usr/local/bin/kubectl; \
    kubectl version --client=true; \
    curl -fsSL "https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/yq_linux_${YQ_ARCH}" \
      -o /usr/local/bin/yq; \
    chmod 0755 /usr/local/bin/yq; \
    yq --version

# Docker CLI (client only, no daemon). ward's read-only `explore` session binds the
# host docker socket so the in-container agent can dispatch a sibling `warded #N`
# headless run; that needs a `docker` client in the image. The static
# tarball ships the full engine - extract only the client binary.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${DOCKER_ARCH}/docker-${DOCKER_VERSION}.tgz" \
      -o /tmp/docker.tgz; \
    tar -xzf /tmp/docker.tgz -C /usr/local/bin --strip-components=1 docker/docker; \
    chmod 0755 /usr/local/bin/docker; \
    rm /tmp/docker.tgz; \
    docker --version

# Tailscale CLI (client only, no daemon). ward containers reach the tower
# (kai-tower-3026 ollama on the tailnet) over the tailnet; the image shipped no
# tailnet client, so an agent could not query tailnet status or route to the
# tower. The static tarball ships the full engine - extract only
# the `tailscale` client binary. This makes the CLI *exist*; bringing up the
# tailnet (auth) is a separate axis ward owns, not baked into the image.
RUN set -eux; \
    . /tmp/arch.env; \
    curl -fsSL "https://pkgs.tailscale.com/stable/tailscale_${TAILSCALE_VERSION}_${TS_ARCH}.tgz" \
      -o /tmp/tailscale.tgz; \
    tar -xzf /tmp/tailscale.tgz -C /usr/local/bin --strip-components=1 \
      "tailscale_${TAILSCALE_VERSION}_${TS_ARCH}/tailscale"; \
    chmod 0755 /usr/local/bin/tailscale; \
    rm /tmp/tailscale.tgz; \
    tailscale version

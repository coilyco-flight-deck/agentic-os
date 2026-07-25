#!/usr/bin/env bash
# Install the Docker client used by the image publisher.

set -euo pipefail

retry_attempts="${DOCKER_DOWNLOAD_RETRY_ATTEMPTS:-5}"
retry_delay_seconds="${DOCKER_DOWNLOAD_RETRY_DELAY_SECONDS:-2}"

download() {
  local url="$1"
  local destination="$2"

  curl \
    --retry "${retry_attempts}" \
    --retry-all-errors \
    --retry-delay "${retry_delay_seconds}" \
    --remove-on-error \
    -fsSL \
    "${url}" \
    -o "${destination}"
}

download \
  "https://download.docker.com/linux/static/stable/x86_64/" \
  /tmp/docker-index.html
docker_cli_ver=$(grep -oE 'docker-[0-9]+\.[0-9]+\.[0-9]+\.tgz' /tmp/docker-index.html \
  | sort -V | tail -1 \
  | sed -E 's/^docker-(.*)\.tgz$/\1/')
download \
  "https://download.docker.com/linux/static/stable/x86_64/docker-${docker_cli_ver}.tgz" \
  /tmp/docker.tgz
tar -xzf /tmp/docker.tgz -C /tmp
install /tmp/docker/docker /usr/local/bin/docker
mkdir -p ~/.docker/cli-plugins
download \
  "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-amd64" \
  ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
rm -rf /tmp/docker /tmp/docker-index.html /tmp/docker.tgz
docker buildx version
docker --version

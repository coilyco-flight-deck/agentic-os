#!/usr/bin/env bash
# Reuse a persistent Buildx builder.

set -euo pipefail

builder_name="${BUILDER_NAME:-aosbuilder}"
builder_driver="${BUILDER_DRIVER:-docker-container}"
echo "buildx before bootstrap"
docker buildx ls
if [ "${INSTALL_BINFMT:-true}" = "true" ]; then
  docker run --privileged --rm tonistiigi/binfmt --install all
fi
if [ "$builder_driver" = "docker" ]; then
  docker buildx use "$builder_name"
  docker buildx inspect "$builder_name" --bootstrap
  echo "buildx after bootstrap"
  docker buildx ls
  exit 0
fi
if [ "$builder_driver" != "docker-container" ]; then
  echo "unsupported buildx driver: $builder_driver" >&2
  exit 1
fi
if ! docker buildx inspect "$builder_name" >/dev/null 2>&1; then
  docker buildx create --name "$builder_name" \
    --driver "$builder_driver" --driver-opt network=host || true
fi
if ! docker buildx inspect "$builder_name" --bootstrap; then
  echo "$builder_name exists but fails to bootstrap. Recreating it (warm cache is lost this once)"
  docker buildx rm -f "$builder_name" 2>/dev/null || true
  docker buildx create --name "$builder_name" \
    --driver "$builder_driver" --driver-opt network=host
  docker buildx inspect "$builder_name" --bootstrap
fi
docker buildx use "$builder_name"
echo "buildx after bootstrap"
docker buildx ls

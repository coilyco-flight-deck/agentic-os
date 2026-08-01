#!/usr/bin/env bash
# Build the declarative image family into the local Docker daemon.

set -euo pipefail

timeout --preserve-status --kill-after=5m "$BUILD_TIMEOUT" \
  env TAG="$TAG" PLATFORM="$PLATFORM" \
  docker buildx bake --progress=plain --file docker/dev-base/docker-bake.hcl

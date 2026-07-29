#!/usr/bin/env bash
# Build the selected image closure into the local Docker daemon.

set -euo pipefail

read -r -a tiers <<< "$BUILD_TIERS"
timeout --preserve-status --kill-after=5m "$BUILD_TIMEOUT" \
  uv run python scripts/dev-base-build.py \
  --registry agentic-os \
  --tag "$TAG" \
  build \
  --load \
  --platforms "$PLATFORM" \
  --tiers "${tiers[@]}"

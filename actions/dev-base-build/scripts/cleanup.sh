#!/usr/bin/env bash
# Remove throwaway tags and cap the persistent validation cache.

set -euo pipefail

for image in \
  "agentic-os:lang-node-${TAG}" \
  "agentic-os:lang-go-${TAG}" \
  "agentic-os:lang-dotnet-${TAG}" \
  "agentic-os:lang-rust-${TAG}" \
  "agentic-os:lang-python-${TAG}" \
  "agentic-os:${TAG}"
do
  docker image rm "$image" >/dev/null 2>&1 || true
done
docker buildx prune \
  --builder "${BUILDER_NAME:-aos-pr-builder}" \
  --force \
  --max-used-space "$CACHE_MAX" || true

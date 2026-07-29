#!/usr/bin/env bash
# Remove throwaway tags and cap the persistent validation cache.

set -euo pipefail

plan="$(
  uv run python scripts/dev-base-build.py \
    --registry agentic-os \
    --tag "$TAG" \
    plan
)"
while IFS= read -r image; do
  docker image rm "$image" >/dev/null 2>&1 || true
done < <(
  PLAN_JSON="$plan" uv run python -c \
    'import json, os; print("\n".join(t["image"] for t in json.loads(os.environ["PLAN_JSON"])["tiers"]))'
)
docker buildx prune \
  --builder "${BUILDER_NAME:-aos-pr-builder}" \
  --force \
  --max-used-space "$CACHE_MAX" || true

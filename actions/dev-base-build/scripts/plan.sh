#!/usr/bin/env bash
# Derive the image closure affected by the pull-request diff.

set -euo pipefail

args=(
  uv run python scripts/dev-base-build.py
  --registry agentic-os
  --tag "$TAG"
  affected
  --head "$HEAD_SHA"
  --github-output "$GITHUB_OUTPUT"
)
if [ -n "$BASE_SHA" ]; then
  args+=(--base "$BASE_SHA")
fi
"${args[@]}"

#!/usr/bin/env bash
# Skip a build or promotion only when every requested target already matches.

set -euo pipefail

if [ "$MODE" = promote ] && [ "$TIER" != full ]; then
  echo "::error::only the full dev-base image is a promotable release product" >&2
  exit 2
fi

tier_tag() {
  if [ "$1" = full ]; then
    printf '%s' "$2"
  else
    printf '%s-%s' "$1" "$2"
  fi
}

manifest_digest() {
  local output
  if ! output=$(docker buildx imagetools inspect "$1" 2>/dev/null); then
    return 0
  fi
  awk '$1 == "Digest:" { print $2; exit }' <<< "$output"
}

target="${IMAGE_BASE}:$(tier_tag "$TIER" "$TAG")"
target_digest=$(manifest_digest "$target")
if [ -z "$target_digest" ]; then
  echo "skip_publish=false" >> "$GITHUB_OUTPUT"
  exit 0
fi

expected_digest=$target_digest
if [ "$MODE" = promote ]; then
  if [ -z "${SOURCE_TAG:-}" ]; then
    echo "::error::source-tag is required in promote mode" >&2
    exit 2
  fi
  source="${IMAGE_BASE}:$(tier_tag "$TIER" "$SOURCE_TAG")"
  expected_digest=$(manifest_digest "$source")
  if [ -z "$expected_digest" ] || [ "$target_digest" != "$expected_digest" ]; then
    echo "skip_publish=false" >> "$GITHUB_OUTPUT"
    exit 0
  fi
fi

aliases="${ALIAS:-} ${EXTRA_ALIASES:-}"
# shellcheck disable=SC2086 # Alias inputs are whitespace-separated tag lists.
for moving_tag in $aliases; do
  alias_ref="${IMAGE_BASE}:$(tier_tag "$TIER" "$moving_tag")"
  if [ "$(manifest_digest "$alias_ref")" != "$expected_digest" ]; then
    echo "skip_publish=false" >> "$GITHUB_OUTPUT"
    exit 0
  fi
done

echo "skip_publish=true" >> "$GITHUB_OUTPUT"

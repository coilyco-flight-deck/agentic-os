#!/usr/bin/env bash
# Assert a moving alias resolves to the digest of the image a run just built.

set -euo pipefail

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

if [ -z "${SOURCE_TAG:-}" ]; then
  echo "::error::source-tag is required in verify mode" >&2
  exit 2
fi

source_ref="${IMAGE_BASE}:$(tier_tag "$TIER" "$SOURCE_TAG")"
source_digest=$(manifest_digest "$source_ref")
if [ -z "$source_digest" ]; then
  echo "::error::${source_ref} does not resolve, so there is nothing this run built" >&2
  exit 1
fi

# TAG plus any aliases, so one call covers the version tag and every moving one.
read -r -a moving_tags <<< "${TAG:-} ${ALIAS:-} ${EXTRA_ALIASES:-}"
if [ "${#moving_tags[@]}" -eq 0 ]; then
  echo "::error::no tag or alias to verify. Verifying nothing is not a pass." >&2
  exit 2
fi

failed=0
for moving_tag in "${moving_tags[@]}"; do
  alias_ref="${IMAGE_BASE}:$(tier_tag "$TIER" "$moving_tag")"
  alias_digest=$(manifest_digest "$alias_ref")
  if [ -z "$alias_digest" ]; then
    echo "::error::${alias_ref} does not resolve. The promotion did not happen." >&2
    failed=1
  elif [ "$alias_digest" != "$source_digest" ]; then
    echo "::error::${alias_ref} is ${alias_digest}, expected ${source_digest} from ${source_ref}. The promotion did not happen, or promoted something else." >&2
    failed=1
  else
    echo "${alias_ref} resolves to ${source_digest}"
  fi
done
exit "$failed"

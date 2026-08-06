#!/usr/bin/env bash

set -euo pipefail

: "${PR_NUMBER:?missing pull-request number}"
: "${PR_BASE_SHA:?missing pull-request base commit}"
: "${PR_HEAD_SHA:?missing pull-request head commit}"
: "${GITHUB_ENV:?missing Forgejo Actions environment file}"

case "$PR_NUMBER" in
  *[!0-9]*) echo "invalid pull-request number" >&2; exit 1 ;;
esac

for sha in "$PR_BASE_SHA" "$PR_HEAD_SHA"; do
  case "$sha" in
    *[!0-9a-fA-F]*) echo "invalid pull-request commit" >&2; exit 1 ;;
  esac
  test "${#sha}" -eq 40 || test "${#sha}" -eq 64
  git cat-file -e "${sha}^{commit}"
done

git switch --detach "$PR_BASE_SHA"
git -c user.name="Forgejo Actions" \
  -c user.email="forgejo-actions@noreply.forgejo.coilysiren.me" \
  merge --no-ff --no-edit "$PR_HEAD_SHA"

{
  printf 'WARD_CI_GITHUB_REF=refs/pull/%s/merge\n' "$PR_NUMBER"
  printf 'WARD_CI_GITHUB_SHA=%s\n' "$(git rev-parse HEAD)"
} >> "$GITHUB_ENV"

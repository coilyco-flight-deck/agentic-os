#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <ward-verb> [args...]" >&2
  exit 2
fi

if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ]; then
  : "${WARD_CI_GITHUB_REF:?missing verified pull-request ref}"
  : "${WARD_CI_GITHUB_SHA:?missing verified pull-request commit}"
  export GITHUB_REF="$WARD_CI_GITHUB_REF"
  export GITHUB_SHA="$WARD_CI_GITHUB_SHA"
fi

exec ward exec "$@"

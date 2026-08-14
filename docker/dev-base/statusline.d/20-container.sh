#!/usr/bin/env bash
# Status-line provider: which warded container this session is inside.
# Self-suppresses on a native host, where ward sets nothing.
set -euo pipefail

[ -n "${WARD_CONTAINER_NAME:-}" ] || exit 0
printf '  [%s]' "${WARD_CONTAINER_NAME}"

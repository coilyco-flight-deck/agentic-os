#!/usr/bin/env bash
# Tab script for `ward agent <mode> work <ref> --new-tab`. Pops a {ref,mode}
# queue entry written by ward and runs the agent in this fresh tab. Successor to
# the retired claude-dispatch-interactive shim (ward#174).

set -u

QUEUE_DIR=/tmp/ward-agent-queue
LOCK_DIR="${QUEUE_DIR}/.lock"
PROJECTS_ROOT="${PROJECTS_ROOT:-${HOME}/projects}"

soft_fail() {
  printf '%s\n' "$1"
  cd "${PROJECTS_ROOT}" || true
  exec "${SHELL:-/bin/zsh}" -l
}

if ! command -v jq >/dev/null 2>&1; then
  soft_fail "agent work: jq not found. Install with 'brew install jq' and re-fire."
fi

# mkdir mutex: macOS has no flock. 50ms backoff, 10s timeout.
acquired=0
for _ in $(seq 1 200); do
  if mkdir "${LOCK_DIR}" 2>/dev/null; then
    acquired=1
    break
  fi
  sleep 0.05
done
if [[ "${acquired}" -ne 1 ]]; then
  soft_fail "agent work: could not acquire ${LOCK_DIR} within 10s. Stale lock? rm -rf ${LOCK_DIR} and retry."
fi

# Unix-nanos filename prefix gives FIFO under lexicographic sort.
JSON_FILE="$(find "${QUEUE_DIR}" -maxdepth 1 -name '*.json' -type f 2>/dev/null | LC_ALL=C sort | head -1)"

if [[ -z "${JSON_FILE}" || ! -f "${JSON_FILE}" ]]; then
  rmdir "${LOCK_DIR}"
  soft_fail "agent work: no pending spawn in ${QUEUE_DIR}. Did 'ward agent <mode> work <ref> --new-tab' write one?"
fi

PAYLOAD="$(cat "${JSON_FILE}")"
rm -f "${JSON_FILE}"
rmdir "${LOCK_DIR}"

REF="$(printf '%s' "${PAYLOAD}" | jq -r '.ref // empty')"
MODE="$(printf '%s' "${PAYLOAD}" | jq -r '.mode // empty')"
TITLE="$(printf '%s' "${PAYLOAD}" | jq -r '.title // empty')"

if [[ -z "${REF}" || -z "${MODE}" ]]; then
  soft_fail "agent work: queue entry ${JSON_FILE} was missing ref / mode fields. Body was: ${PAYLOAD}"
fi

# The container clones the repo fresh, so cwd is irrelevant - start in the
# projects root for a tidy prompt.
cd "${PROJECTS_ROOT}" || true

if [[ -n "${TITLE}" ]]; then
  printf '%s\n' "${REF}: ${TITLE}"
else
  printf '%s\n' "${REF}"
fi

exec ward agent "${MODE}" work "${REF}"

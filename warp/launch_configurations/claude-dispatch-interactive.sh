#!/usr/bin/env bash
# Tab script for ward dispatch interactive. See ward#280.

set -u

QUEUE_DIR=/tmp/ward-dispatch-queue
LOCK_DIR="${QUEUE_DIR}/.lock"
PROJECTS_ROOT="${HOME}/projects/coilysiren"

soft_fail() {
  printf '%s\n' "$1"
  cd "${PROJECTS_ROOT}" || true
  exec "${SHELL:-/bin/zsh}" -l
}

if ! command -v jq >/dev/null 2>&1; then
  soft_fail "dispatch interactive: jq not found. Install with 'brew install jq' and re-fire the dispatch."
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
  soft_fail "dispatch interactive: could not acquire ${LOCK_DIR} within 10s. Stale lock? rm -rf ${LOCK_DIR} and retry."
fi

# Unix-nanos filename prefix gives FIFO under lexicographic sort.
JSON_FILE="$(find "${QUEUE_DIR}" -maxdepth 1 -name '*.json' -type f 2>/dev/null | LC_ALL=C sort | head -1)"

if [[ -z "${JSON_FILE}" || ! -f "${JSON_FILE}" ]]; then
  rmdir "${LOCK_DIR}"
  soft_fail "dispatch interactive: no pending dispatch in ${QUEUE_DIR}. Did 'ward dispatch interactive <ref>' write one?"
fi

PAYLOAD="$(cat "${JSON_FILE}")"
rm -f "${JSON_FILE}"
rmdir "${LOCK_DIR}"

REF="$(printf '%s' "${PAYLOAD}" | jq -r '.ref // empty')"
TITLE="$(printf '%s' "${PAYLOAD}" | jq -r '.title // empty')"
CWD="$(printf '%s' "${PAYLOAD}" | jq -r '.cwd // empty')"
PROMPT="$(printf '%s' "${PAYLOAD}" | jq -r '.prompt // empty')"

if [[ -z "${REF}" || -z "${CWD}" || -z "${PROMPT}" ]]; then
  soft_fail "dispatch interactive: queue entry ${JSON_FILE} was missing ref / cwd / prompt fields. Body was: ${PAYLOAD}"
fi

if [[ ! -d "${CWD}" ]]; then
  soft_fail "dispatch interactive: cwd ${CWD} does not exist. Clone the repo first, then re-fire."
fi

cd "${CWD}" || soft_fail "dispatch interactive: cd ${CWD} failed."

if [[ -n "${TITLE}" ]]; then
  printf '%s\n' "${REF}: ${TITLE}"
else
  printf '%s\n' "${REF}"
fi

exec claude "${PROMPT}"

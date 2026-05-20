#!/usr/bin/env bash
# claude-dispatch-interactive.sh - consumed by the same-named Warp launch
# config (claude-dispatch-interactive.yaml) and tab config
# (../tab_configs/claude-dispatch-interactive.toml).
#
# Contract with `coily dispatch interactive <ref>` (coilysiren/coily#280):
#   1. coily writes one JSON file per dispatch under
#      /tmp/coily-dispatch-queue/ named <unix-nanos>-<8hex>.json, mode
#      0600. Payload carries ref, title, cwd, prompt.
#   2. coily fires `open warp(preview)://(tab_config|launch)/claude-dispatch-interactive`.
#   3. This shim acquires the queue mutex (mkdir on .lock), pops the
#      oldest .json file, parses ref / title / cwd / prompt via jq,
#      echoes "<ref>: <title>" for at-a-glance identification (#279),
#      cd's into cwd, and execs claude with the prompt body. Exec
#      happens after the lock is released so concurrent tabs do not
#      serialize on claude startup.
#
# Soft-fail modes (all land the operator in a plain shell with a hint
# rather than crashing the tab):
#   - jq missing: print install hint
#   - queue lock unavailable for 10s: print abort hint
#   - queue empty (stray tab open from the palette, not a dispatch fire):
#     print did-you-mean hint

set -u

QUEUE_DIR=/tmp/coily-dispatch-queue
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

# mkdir is the POSIX-portable mutex (flock is not on macOS by default).
# 50ms backoff, 10s timeout. The critical section is short (find + read
# + unlink), so contention rarely lasts more than one tick.
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

# Total filename order is unix-nanos prefix, so plain lexicographic
# sort gives FIFO. `find` avoids the no-match-literal-pattern glob trap.
JSON_FILE="$(find "${QUEUE_DIR}" -maxdepth 1 -name '*.json' -type f 2>/dev/null | LC_ALL=C sort | head -1)"

if [[ -z "${JSON_FILE}" || ! -f "${JSON_FILE}" ]]; then
  rmdir "${LOCK_DIR}"
  soft_fail "dispatch interactive: no pending dispatch in ${QUEUE_DIR}. Did 'coily dispatch interactive <ref>' write one?"
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

# Self-identifying header for the dispatched tab (#279). Empty-title
# guard: print just the ref if coily could not resolve a title.
if [[ -n "${TITLE}" ]]; then
  printf '%s\n' "${REF}: ${TITLE}"
else
  printf '%s\n' "${REF}"
fi

exec claude "${PROMPT}"

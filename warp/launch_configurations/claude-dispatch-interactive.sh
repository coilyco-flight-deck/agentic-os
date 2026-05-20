#!/usr/bin/env bash
# claude-dispatch-interactive.sh - consumed by the same-named Warp launch
# config (claude-dispatch-interactive.yaml).
#
# Contract with `coily dispatch interactive <ref>`:
#   1. coily writes the prompt body to /tmp/coily-dispatch-prompt.txt
#      with mode 0600. Format: a single line "Work on issue
#      coilysiren/<repo>#<N>" plus a trailing newline.
#   2. coily fires `open warp://launch/claude-dispatch-interactive`.
#   3. This script reads the scratch file, greps the ref out of the
#      prompt body, derives the local checkout at
#      ~/projects/coilysiren/<repo>, cd's in, execs claude with the
#      prompt body, then deletes the scratch file.
#
# Soft-fail mode: if the scratch file is missing the script lands the
# operator in a plain shell at ~/projects/coilysiren with a printed hint,
# rather than crashing the tab. Same shape as coily's copy-paste fallback.

set -u

SCRATCH=/tmp/coily-dispatch-prompt.txt
PROJECTS_ROOT="${HOME}/projects/coilysiren"

if [[ ! -f "${SCRATCH}" ]]; then
  printf 'dispatch interactive: scratch file %s missing. Did `coily dispatch interactive <ref>` write it?\n' "${SCRATCH}"
  cd "${PROJECTS_ROOT}" || true
  exec "${SHELL:-/bin/zsh}" -l
fi

PROMPT="$(cat "${SCRATCH}")"
REF="$(printf '%s' "${PROMPT}" | grep -oE 'coilysiren/[A-Za-z0-9._-]+#[0-9]+' | head -1)"

if [[ -z "${REF}" ]]; then
  printf 'dispatch interactive: scratch file %s did not contain a coilysiren/<repo>#<N> ref. Body was:\n%s\n' "${SCRATCH}" "${PROMPT}"
  rm -f "${SCRATCH}"
  cd "${PROJECTS_ROOT}" || true
  exec "${SHELL:-/bin/zsh}" -l
fi

REPO="${REF#coilysiren/}"
REPO="${REPO%#*}"
TARGET_DIR="${PROJECTS_ROOT}/${REPO}"

if [[ ! -d "${TARGET_DIR}" ]]; then
  printf 'dispatch interactive: local checkout missing at %s. Clone it first, then re-run.\n' "${TARGET_DIR}"
  rm -f "${SCRATCH}"
  cd "${PROJECTS_ROOT}" || true
  exec "${SHELL:-/bin/zsh}" -l
fi

cd "${TARGET_DIR}" || {
  printf 'dispatch interactive: cd %s failed.\n' "${TARGET_DIR}"
  rm -f "${SCRATCH}"
  exec "${SHELL:-/bin/zsh}" -l
}

rm -f "${SCRATCH}"
exec claude "${PROMPT}"

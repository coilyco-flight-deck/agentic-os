#!/usr/bin/env bash
# claude-dispatch-interactive.sh - consumed by the same-named Warp launch
# config (claude-dispatch-interactive.yaml).
#
# Contract with `coily dispatch interactive <ref>`:
#   1. coily writes the prompt body to /tmp/coily-dispatch-prompt.txt
#      with mode 0600. First sentence contains "coilysiren/<repo>#<N>"
#      which this script greps out to derive cwd.
#   2. coily writes a self-identifying header "<ref>: <title>" to
#      /tmp/coily-dispatch-title.txt with mode 0600 alongside the
#      prompt. Optional - missing title file is a soft-fail
#      (older coily releases don't write it).
#   3. coily fires `open warp://launch/claude-dispatch-interactive`.
#   4. This script reads the scratch file, greps the ref out of the
#      prompt body, derives the local checkout at
#      ~/projects/coilysiren/<repo>, cd's in, echoes the title header
#      so the tab self-identifies before claude takes over, execs
#      claude with the prompt body, then deletes both files.
#
# Soft-fail mode: if the scratch file is missing the script lands the
# operator in a plain shell at ~/projects/coilysiren with a printed hint,
# rather than crashing the tab. Same shape as coily's copy-paste fallback.

set -u

SCRATCH=/tmp/coily-dispatch-prompt.txt
TITLE=/tmp/coily-dispatch-title.txt
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
  rm -f "${SCRATCH}" "${TITLE}"
  cd "${PROJECTS_ROOT}" || true
  exec "${SHELL:-/bin/zsh}" -l
fi

REPO="${REF#coilysiren/}"
REPO="${REPO%#*}"
TARGET_DIR="${PROJECTS_ROOT}/${REPO}"

if [[ ! -d "${TARGET_DIR}" ]]; then
  printf 'dispatch interactive: local checkout missing at %s. Clone it first, then re-run.\n' "${TARGET_DIR}"
  rm -f "${SCRATCH}" "${TITLE}"
  cd "${PROJECTS_ROOT}" || true
  exec "${SHELL:-/bin/zsh}" -l
fi

cd "${TARGET_DIR}" || {
  printf 'dispatch interactive: cd %s failed.\n' "${TARGET_DIR}"
  rm -f "${SCRATCH}" "${TITLE}"
  exec "${SHELL:-/bin/zsh}" -l
}

# Self-identify the tab before claude takes over: print "<ref>: <title>"
# from the sidecar coily wrote alongside the prompt scratch file, so a
# human eyeballing the tab sees what the session is working on without
# waiting for claude's first turn (coilysiren/coily#279). Soft-fail
# silently if the sidecar is missing - older coily releases don't write
# it and the prompt-scratch contract is the only hard requirement.
if [[ -f "${TITLE}" ]]; then
  printf '%s\n' "$(cat "${TITLE}")"
fi

rm -f "${SCRATCH}" "${TITLE}"
exec claude "${PROMPT}"

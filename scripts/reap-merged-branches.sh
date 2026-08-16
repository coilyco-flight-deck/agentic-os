#!/usr/bin/env bash
# Deletes local branches whose commits all exist on a remote, across the
# resident repositories. Reports the rest rather than touching them.
#
# WHY THIS IS NOT THE NATIVE SWEEP'S JOB TODAY. The ten-minute fleet pass in
# aos-cli/native_shadow.go switches a clean, inactive, remotely-recoverable
# checkout to main and deletes THAT branch, and it releases worktrees held by
# dead session leases. Neither path reaps a local branch that is merely sitting
# there un-checked-out, so ordinary PR branches accumulate for the life of the
# clone. Measured 2026-08-16: 429 local branches across 11 repositories, 253 of
# them reapable here. See agentic-os#1084 for the durable fix.
#
# THE SAFETY RULE IS THE SAME ONE THE SWEEP USES. A branch is deleted only when
# `rev-list <branch> --not --remotes` is empty, meaning every commit on it is
# reachable from some remote. A branch holding even one local-only commit is
# reported and kept. That is deliberately stricter than `git branch --merged`,
# which would delete a branch whose commits are merged into main but never
# pushed anywhere.
#
# Default is a dry run. Pass --apply to actually delete.
set -euo pipefail

apply=0
case "${1:-}" in
  --apply) apply=1 ;;
  --dry-run | "") ;;
  *)
    echo "usage: $0 [--dry-run|--apply]" >&2
    exit 2
    ;;
esac

projects="${AOS_PROJECTS_ROOT:-${HOME}/projects}"
if [ ! -d "${projects}" ]; then
  echo "no projects root at ${projects}" >&2
  exit 1
fi

total_safe=0
total_kept=0

while read -r gitdir; do
  repo="$(dirname "${gitdir}")"
  name="$(basename "${repo}")"
  # A *-workdir checkout is Kai's manual space and stays outside automation.
  case "${name}" in *-workdir) continue ;; esac

  current="$(git -C "${repo}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
  # Read once per repository. Asking per branch costs one git invocation each
  # and made a 429-branch fleet take minutes.
  checked_out="$(git -C "${repo}" worktree list --porcelain 2>/dev/null |
    sed -n 's|^branch refs/heads/||p')"
  safe=()
  kept=()
  while read -r branch; do
    [ -n "${branch}" ] || continue
    [ "${branch}" = "main" ] && continue
    # Never touch the checked-out branch, or one checked out in a linked
    # worktree - git refuses the delete and the run would abort under set -e.
    [ "${branch}" = "${current}" ] && continue
    if printf '%s\n' "${checked_out}" | grep -qxF "${branch}"; then
      continue
    fi
    if [ -z "$(git -C "${repo}" rev-list "refs/heads/${branch}" --not --remotes 2>/dev/null)" ]; then
      safe+=("${branch}")
    else
      kept+=("${branch}")
    fi
  done < <(git -C "${repo}" for-each-ref --format='%(refname:short)' refs/heads/ 2>/dev/null)

  [ "${#safe[@]}" -eq 0 ] && [ "${#kept[@]}" -eq 0 ] && continue
  printf '%-24s safe=%-4s holding-unpushed=%s\n' "${name}" "${#safe[@]}" "${#kept[@]}"
  total_safe=$((total_safe + ${#safe[@]}))
  total_kept=$((total_kept + ${#kept[@]}))

  for branch in ${kept+"${kept[@]}"}; do
    n="$(git -C "${repo}" rev-list --count "refs/heads/${branch}" --not --remotes)"
    printf '    keep  %-52s %s local-only commit(s)\n' "${branch}" "${n}"
  done

  if [ "${apply}" -eq 1 ]; then
    for branch in ${safe+"${safe[@]}"}; do
      git -C "${repo}" branch -D "${branch}" >/dev/null
    done
  fi
done < <(find "${projects}" -maxdepth 3 -name .git -type d 2>/dev/null | sort)

echo
if [ "${apply}" -eq 1 ]; then
  echo "deleted ${total_safe} fully-pushed branch(es); kept ${total_kept} holding local-only commits"
else
  echo "would delete ${total_safe} fully-pushed branch(es); would keep ${total_kept} holding local-only commits"
  echo "re-run with --apply to delete"
fi

#!/usr/bin/env bash
# Second status-line row for this repo: the git checkouts currently on disk, as
# org/repo, plus the ones that have appeared since a persisted baseline. Repos
# quietly re-clone themselves back during dev work; this surfaces the set on
# disk and names the ones that snuck back, so the drift stops going unnoticed.
#
# scripts/agent-name.sh runs $project_dir/.agentic-os/statusline.sh and appends
# its stdout as a second row. See docs/repo-tracker.md.
set -euo pipefail

# Scan root: the org dirs live at <root>/<org>/<repo>. Env-overridable.
repos_root="${AOS_REPOS_ROOT:-$HOME/projects}"
[ -d "$repos_root" ] || exit 0

# Current org/repo set: every <root>/<org>/<repo> that is a git checkout. .git
# is a dir for normal clones, a file for worktrees/submodules, so test -e.
current="$(
  for org in "$repos_root"/*/; do
    org_name="$(basename "$org")"
    for repo in "$org"*/; do
      [ -e "$repo/.git" ] || continue
      printf '%s/%s\n' "$org_name" "$(basename "$repo")"
    done
  done 2>/dev/null | sort -u
)"
[ -n "$current" ] || exit 0
count="$(printf '%s\n' "$current" | wc -l | tr -d ' ')"

# Baseline set persists across sessions; delete it to re-anchor once you accept
# the current checkouts. First run seeds it from current (nothing is new yet).
state_dir="${XDG_CACHE_HOME:-$HOME/.cache}/agentic-os/repos"
mkdir -p "$state_dir"
key="$(printf '%s' "$repos_root" | shasum 2>/dev/null | cut -c1-12)"
[ -n "$key" ] || key="default"
base_file="$state_dir/$key.baseline"
[ -s "$base_file" ] || printf '%s\n' "$current" >"$base_file"

# New = on disk now but absent from the baseline (the ones that snuck back).
new="$(comm -23 <(printf '%s\n' "$current") <(sort -u "$base_file") 2>/dev/null || true)"

reset="\033[0m"
if [ -z "$new" ]; then
  printf '  📦 \033[32m%s repos%b' "$count" "$reset"   # green: matches baseline
  exit 0
fi

new_count="$(printf '%s\n' "$new" | wc -l | tr -d ' ')"
# Join the first few new names with ", "; collapse the rest into "+N more".
show=""; shown=0
while IFS= read -r r; do
  [ -n "$r" ] || continue
  show="${show:+$show, }$r"; shown=$((shown + 1))
  [ "$shown" -ge 4 ] && break
done < <(printf '%s\n' "$new")
[ "$new_count" -gt "$shown" ] && show="$show, +$((new_count - shown)) more"

# Yellow for a little drift, orange once a lot has piled back on.
if [ "$new_count" -ge 4 ]; then color="\033[38;5;208m"; else color="\033[33m"; fi
printf '  📦 %b%s repos  +%s: %s%b' "$color" "$count" "$new_count" "$show" "$reset"

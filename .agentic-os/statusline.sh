#!/usr/bin/env bash
# Second status-line row for this repo: git checkouts on disk that are NOT on
# the expected-repos list, i.e. the strays to remove. Repos quietly re-clone
# themselves back during dev work; this names the ones that should not be here.
#
# Expected list: a file of repos that SHOULD be on disk, one per line, each
# "owner/name" or bare "name" ('#' comments and blank lines ignored). Resolved
# from $AOS_REPOS_EXPECTED, else ~/.config/agentic-os/repos-on-disk.txt. Matching
# is by repo name, so the list may use either form. With no list, just the count
# shows. See docs/repo-tracker.md.
#
# scripts/agent-name.sh runs this and appends its stdout as a second row.
set -euo pipefail

# Scan root: the org dirs live at <root>/<org>/<repo>. Env-overridable.
repos_root="${AOS_REPOS_ROOT:-$HOME/projects}"
[ -d "$repos_root" ] || exit 0

# Fleet orgs (the orgs you own): only checkouts under these are considered, so
# third-party upstreams never read as strays. Empty list -> every org in scope.
fleet_file="${AOS_FLEET_ORGS:-${XDG_CONFIG_HOME:-$HOME/.config}/agentic-os/fleet-orgs.txt}"
fleet_orgs=""
[ -r "$fleet_file" ] && fleet_orgs="$(sed 's/#.*//' "$fleet_file" | tr -d '[:blank:]' | grep -v '^$' | sort -u)"

# Current org/repo checkouts: <root>/<org>/<repo> with a .git (dir for clones,
# file for worktrees/submodules, so test -e), restricted to the fleet orgs.
current="$(
  for org in "$repos_root"/*/; do
    org_name="$(basename "$org")"
    [ -z "$fleet_orgs" ] || printf '%s\n' "$fleet_orgs" | grep -qxF "$org_name" || continue
    for repo in "$org"*/; do
      [ -e "$repo/.git" ] || continue
      printf '%s/%s\n' "$org_name" "$(basename "$repo")"
    done
  done 2>/dev/null | sort -u
)"
[ -n "$current" ] || exit 0
count="$(printf '%s\n' "$current" | wc -l | tr -d ' ')"

reset="\033[0m"

# Expected list. Without a readable one, just show the count (nothing to flag).
expected_file="${AOS_REPOS_EXPECTED:-${XDG_CONFIG_HOME:-$HOME/.config}/agentic-os/repos-on-disk.txt}"
if [ ! -r "$expected_file" ]; then
  printf '  📦 \033[32m%s repos%b' "$count" "$reset"
  exit 0
fi

# Expected repo names: strip comments/whitespace, drop any owner/ prefix, dedup.
exp_names="$(sed 's/#.*//' "$expected_file" | tr -d '[:blank:]' | sed 's#.*/##' | grep -v '^$' | sort -u)"

# Stray = on disk but its repo name is not expected.
stray=""
while IFS= read -r r; do
  printf '%s\n' "$exp_names" | grep -qxF "${r##*/}" || stray="${stray:+$stray
}$r"
done < <(printf '%s\n' "$current")

if [ -z "$stray" ]; then
  printf '  📦 \033[32m%s repos, none stray%b' "$count" "$reset"
  exit 0
fi

s_count="$(printf '%s\n' "$stray" | wc -l | tr -d ' ')"
# Join the first few stray names with ", "; collapse the rest into "+N more".
show=""; shown=0
while IFS= read -r r; do
  [ -n "$r" ] || continue
  show="${show:+$show, }$r"; shown=$((shown + 1))
  [ "$shown" -ge 4 ] && break
done < <(printf '%s\n' "$stray")
[ "$s_count" -gt "$shown" ] && show="$show, +$((s_count - shown)) more"

# Orange for a few strays, bold red once a lot have piled back on.
if [ "$s_count" -ge 4 ]; then color="\033[1;91m"; else color="\033[38;5;208m"; fi
printf '  📦 %b%s to remove: %s%b' "$color" "$s_count" "$show" "$reset"

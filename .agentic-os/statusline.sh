#!/usr/bin/env bash
# Second status-line row for this repo: the working-tree disk footprint and how
# much it has grown since a persisted baseline. Repos quietly accrete build
# artifacts, caches, and .git bloat between cleanups; this surfaces that drift
# inline so it stops sneaking back onto disk unnoticed.
#
# scripts/agent-name.sh runs $project_dir/.agentic-os/statusline.sh and appends
# its stdout as a second row. See docs/features-agents-sessions.md. Measurement
# is cached and refreshed in the background, so the status line stays instant no
# matter how large the tree grows (du never runs on the foreground path after
# the first reading).
set -euo pipefail

# Repo root = this script's parent's parent (.agentic-os/statusline.sh -> repo).
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$script_dir/.." && pwd)"

# Tunables, env-overridable.
refresh_secs="${AOS_DISK_REFRESH_SECS:-120}"   # min seconds between du runs
warn_kb="${AOS_DISK_WARN_KB:-51200}"           # +50M growth -> orange
crit_kb="${AOS_DISK_CRIT_KB:-256000}"          # +250M growth -> red

# Per-repo state under the shared agentic-os cache. The baseline persists across
# sessions, so growth tracks over days; delete the .baseline file to re-anchor.
state_dir="${XDG_CACHE_HOME:-$HOME/.cache}/agentic-os/disk"
mkdir -p "$state_dir"
key="$(printf '%s' "$repo" | shasum 2>/dev/null | cut -c1-12)"
[ -n "$key" ] || key="$(printf '%s' "$repo" | cksum | cut -d' ' -f1)"
cur_file="$state_dir/$key.current"     # "<epoch> <size_kb>"
base_file="$state_dir/$key.baseline"   # "<epoch> <size_kb>"
lock_dir="$state_dir/$key.lock"

now="$(date +%s)"

# du the tree, write current, seed the baseline once. The temp+mv keeps readers
# from seeing a half-written file.
measure() {
  local size
  size="$(du -sk "$repo" 2>/dev/null | awk '{print $1}')" || return 0
  [ -n "$size" ] || return 0
  printf '%s %s\n' "$(date +%s)" "$size" >"$cur_file.tmp" && mv "$cur_file.tmp" "$cur_file"
  [ -s "$base_file" ] || printf '%s %s\n' "$(date +%s)" "$size" >"$base_file"
}

# First-ever run for this repo: measure synchronously so there is something to
# show. Every later refresh happens in the background.
[ -s "$cur_file" ] || measure
read -r cur_epoch cur_kb <"$cur_file" 2>/dev/null || exit 0
[ -n "${cur_kb:-}" ] || exit 0

# Stale reading? Break a dead lock, then kick a background refresh and keep
# showing the cached value. mkdir is the atomic lock; one du runs at a time.
if [ $((now - cur_epoch)) -ge "$refresh_secs" ]; then
  if [ -d "$lock_dir" ]; then
    lock_m="$(stat -f %m "$lock_dir" 2>/dev/null || stat -c %Y "$lock_dir" 2>/dev/null || echo "$now")"
    [ $((now - lock_m)) -ge $((refresh_secs * 5)) ] && rmdir "$lock_dir" 2>/dev/null || true
  fi
  if mkdir "$lock_dir" 2>/dev/null; then
    ( trap 'rmdir "$lock_dir" 2>/dev/null || true' EXIT; measure ) >/dev/null 2>&1 &
  fi
fi

read -r base_epoch base_kb <"$base_file" 2>/dev/null || { base_epoch="$cur_epoch"; base_kb="$cur_kb"; }

human() {  # KB -> compact human size
  awk -v k="$1" 'BEGIN{
    s=k; u="K";
    if (s>=1048576){s/=1048576;u="G"} else if (s>=1024){s/=1024;u="M"}
    if (u=="K") printf "%d%s", s, u; else printf "%.1f%s", s, u
  }'
}
signed_human() {  # signed KB -> +/- compact human size
  local k="$1" sign="+"
  if [ "$k" -lt 0 ]; then sign="-"; k=$(( -k )); fi
  printf '%s%s' "$sign" "$(human "$k")"
}
age() {  # epoch -> compact age (3d / 5h / 12m / 9s)
  local secs=$(( now - $1 ))
  [ "$secs" -lt 0 ] && secs=0
  if   [ "$secs" -ge 86400 ]; then printf '%dd' $(( secs / 86400 ))
  elif [ "$secs" -ge 3600  ]; then printf '%dh' $(( secs / 3600 ))
  elif [ "$secs" -ge 60    ]; then printf '%dm' $(( secs / 60 ))
  else printf '%ds' "$secs"; fi
}

delta=$(( cur_kb - base_kb ))

# Color and arrow by growth since baseline: green flat/shrank, yellow mild,
# orange past warn_kb, bold red past crit_kb.
if   [ "$delta" -le 0 ];          then color="\033[32m";        arrow="•"
elif [ "$delta" -ge "$crit_kb" ]; then color="\033[1;91m";      arrow="▲"
elif [ "$delta" -ge "$warn_kb" ]; then color="\033[38;5;208m";  arrow="▲"
else                                   color="\033[33m";        arrow="▲"; fi
[ "$delta" -lt 0 ] && arrow="▼"
reset="\033[0m"

printf '  📦 disk %s  %b%s %s/%s%b' \
  "$(human "$cur_kb")" "$color" "$arrow" "$(signed_human "$delta")" "$(age "$base_epoch")" "$reset"

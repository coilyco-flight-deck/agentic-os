#!/usr/bin/env bash
# Across-the-room GitHub API health monitor. See docs/github-pulse.md.

set -u

ATTEMPTS=3
SLEEP_BETWEEN=10
HISTORY=()
HISTORY_MAX=30

# Resources with window length in seconds. Order = display order.
RESOURCES=(
  "core:3600"
  "search:60"
  "graphql:3600"
  "code_search:60"
  "dependency_snapshots:3600"
)

check_once() {
  # Emits "<http_code>|<json>". Empty on failure.
  local out code body
  out=$(gh api --include /rate_limit 2>/dev/null) || true
  code=$(printf '%s\n' "$out" | awk 'NR == 1 && /^HTTP\// { print $2 }')
  body=$(printf '%s\n' "$out" | awk 'found || /^[[:space:]]*[{[]/ { found = 1; print }')
  if [[ -z "$code" ]]; then
    echo "000|"
    return
  fi
  echo "$code|$body"
}

check_with_retries() {
  local out code
  for i in $(seq 1 $ATTEMPTS); do
    out=$(check_once)
    code="${out%%|*}"
    if [[ "$code" == "200" ]]; then echo "$out"; return; fi
    sleep 1
  done
  echo "${out:-000|}"
}

# Format seconds as "1h23m45s" / "23m45s" / "45s"
fmt_duration() {
  local s=$1
  if (( s < 0 )); then s=0; fi
  if (( s >= 3600 )); then
    printf '%dh%02dm%02ds' $(( s / 3600 )) $(( (s % 3600) / 60 )) $(( s % 60 ))
  elif (( s >= 60 )); then
    printf '%dm%02ds' $(( s / 60 )) $(( s % 60 ))
  else
    printf '%ds' "$s"
  fi
}

# Pace = used% - elapsed%. Positive burns faster than the clock.
calc_pace() {
  local limit=$1 remaining=$2 reset=$3 window=$4 now=$5
  if (( limit <= 0 || window <= 0 )); then echo "0|  |\e[2m"; return; fi
  local used=$(( limit - remaining ))
  local elapsed=$(( window - (reset - now) ))
  if (( elapsed < 0 )); then elapsed=0; fi
  if (( elapsed > window )); then elapsed=$window; fi
  local used_pct=$(( used * 100 / limit ))
  local elapsed_pct=$(( elapsed * 100 / window ))
  local pace=$(( used_pct - elapsed_pct ))
  local glyph color
  if   (( pace >= 25 )); then glyph="🔥"; color="\e[1;31m"
  elif (( pace >= 5  )); then glyph="⚠️ "; color="\e[1;33m"
  elif (( pace >= -5 )); then glyph="✅"; color="\e[1;32m"
  else                        glyph="💤"; color="\e[1;36m"
  fi
  echo "${pace}|${glyph}|${color}"
}

paint() {
  local payload="$1"
  local code="${payload%%|*}"
  local body="${payload#*|}"
  local now_ts
  now_ts=$(date +%s)
  local now
  now=$(date '+%H:%M:%S')

  clear
  local cols
  cols=$(tput cols 2>/dev/null || echo 80)

  local banner glyph word mark
  case "$code" in
    200)   banner="\e[1;42;97m"; glyph="✅"; word="GITHUB API IS UP"; mark="🟩" ;;
    000|"") banner="\e[1;41;97m"; glyph="🔥"; word="NO RESPONSE   "; mark="🟥" ;;
    5*)    banner="\e[1;41;97m"; glyph="💥"; word="GITHUB IS DOWN "; mark="🟥" ;;
    401)   banner="\e[1;43;30m"; glyph="🔐"; word="AUTH FAILED  "; mark="🟨" ;;
    403)   banner="\e[1;43;30m"; glyph="🚧"; word="FORBIDDEN    "; mark="🟨" ;;
    4*)    banner="\e[1;43;30m"; glyph="⚠️ "; word="CLIENT ERROR ($code)"; mark="🟨" ;;
    *)     banner="\e[1;43;30m"; glyph="❓"; word="WEIRD ($code)  "; mark="🟨" ;;
  esac

  HISTORY+=("$mark")
  if (( ${#HISTORY[@]} > HISTORY_MAX )); then
    HISTORY=("${HISTORY[@]: -$HISTORY_MAX}")
  fi

  echo
  echo
  printf "${banner}"
  printf '%*s\n' "$cols" ''
  printf '%*s\n' "$cols" ''
  local line="    ${glyph}    ${word}    ${glyph}    "
  local pad=$(( (cols - ${#line}) / 2 ))
  printf '%*s%s%*s\n' "$pad" '' "$line" "$pad" ''
  printf '%*s\n' "$cols" ''
  printf '%*s\n' "$cols" ''
  printf "\e[0m"
  echo
  echo
  printf "       \e[1;97mlast check:\e[0m  %s   \e[2m(http %s)\e[0m\n" "$now" "$code"
  echo

  if [[ "$code" != "200" && -n "$body" ]]; then
    local message
    message=$(printf '%s' "$body" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('message', ''))
except Exception:
    print('')
" 2>/dev/null)
    if [[ -n "$message" ]]; then
      printf "       \e[1;97mmessage:\e[0m     %s\n" "$message"
      if [[ "$code" == "401" ]]; then
        printf "       \e[2mrun: gh auth login -h github.com\e[0m\n"
      fi
      echo
    fi
  fi

  if [[ "$code" == "200" && -n "$body" ]]; then
    printf "       \e[1;97m%-22s  %-15s  %-12s  %s\e[0m\n" "resource" "usage" "pace" "resets"
    printf "       \e[2m%s\e[0m\n" "──────────────────────  ───────────────  ────────────  ──────────"
    for entry in "${RESOURCES[@]}"; do
      local name="${entry%:*}"
      local window="${entry#*:}"
      local triple
      triple=$(printf '%s' "$body" | python3 -c "
import sys, json
d = json.load(sys.stdin).get('resources', {}).get('$name', {})
print(f\"{d.get('limit',0)}|{d.get('remaining',0)}|{d.get('reset',0)}\")
" 2>/dev/null)
      if [[ -z "$triple" ]]; then continue; fi
      IFS='|' read -r r_limit r_remaining r_reset <<<"$triple"
      if (( r_limit == 0 )); then continue; fi
      local r_used=$(( r_limit - r_remaining ))
      local pace_info
      pace_info=$(calc_pace "$r_limit" "$r_remaining" "$r_reset" "$window" "$now_ts")
      IFS='|' read -r pace pace_glyph pace_color <<<"$pace_info"
      local reset_in
      reset_in=$(fmt_duration $(( r_reset - now_ts )))
      local pace_str
      if (( pace > 0 )); then pace_str="+${pace}%"; else pace_str="${pace}%"; fi
      printf "       %-22s  \e[1m%5d / %-5d\e[0m   ${pace_color}%-5s %s\e[0m   \e[2m%s\e[0m\n" \
        "$name" "$r_used" "$r_limit" "$pace_str" "$pace_glyph" "$reset_in"
    done
    echo
  fi

  printf "       \e[1;97mhistory:\e[0m     "
  printf '%s' "${HISTORY[@]}"
  echo
  echo
  printf "       \e[2mpolling every %ss, %s attempts per tick. pace = used%% - elapsed%%. ctrl-c to stop.\e[0m\n" "$SLEEP_BETWEEN" "$ATTEMPTS"
}

trap 'echo; echo "bye 👋"; exit 0' INT

while true; do
  payload=$(check_with_retries)
  paint "$payload"
  sleep "$SLEEP_BETWEEN"
done

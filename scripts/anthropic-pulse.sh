#!/usr/bin/env bash
# Across-the-room Anthropic / Claude health monitor.

set -u

ATTEMPTS=3
SLEEP_BETWEEN=15
HISTORY=()
HISTORY_MAX=40
LATENCY_HISTORY=()

STATUS_URL="https://status.claude.com/api/v2/summary.json"

COMPONENTS=(
  "API"
  "claude.ai"
  "Claude Code"
  "Console"
)

check_once() {
  local tmp body code latency

  tmp=$(mktemp)

  latency=$(curl \
    -sS \
    -o "$tmp" \
    -w '%{http_code}|%{time_total}' \
    "$STATUS_URL" 2>/dev/null)

  code="${latency%%|*}"
  latency="${latency#*|}"

  body=$(cat "$tmp" 2>/dev/null)
  rm -f "$tmp"

  echo "${code}|${latency}|${body}"
}

check_with_retries() {
  local out code

  for i in $(seq 1 $ATTEMPTS); do
    out=$(check_once)
    code="${out%%|*}"

    if [[ "$code" == "200" ]]; then
      echo "$out"
      return
    fi

    sleep 1
  done

  echo "${out:-000|0|}"
}

fmt_duration() {
  local s=$1

  if (( s < 0 )); then s=0; fi

  if (( s >= 3600 )); then
    printf '%dh%02dm%02ds' \
      $(( s / 3600 )) \
      $(( (s % 3600) / 60 )) \
      $(( s % 60 ))
  elif (( s >= 60 )); then
    printf '%dm%02ds' \
      $(( s / 60 )) \
      $(( s % 60 ))
  else
    printf '%ds' "$s"
  fi
}

latency_grade() {
  local ms=$1

  if (( ms < 250 )); then
    echo "⚡ FAST|\e[1;32m"
  elif (( ms < 800 )); then
    echo "🚶 NORMAL|\e[1;33m"
  else
    echo "🐢 SLOW|\e[1;31m"
  fi
}

extract_status() {
  python3 - <<'PY'
import json, sys

try:
    d = json.load(sys.stdin)

    overall = d.get("status", {}).get("description", "Unknown")
    incidents = d.get("incidents", [])

    print(overall)

    if incidents:
        latest = incidents[0]
        print(latest.get("name", "Unnamed incident"))
        print(latest.get("status", "unknown"))
        print(latest.get("created_at", ""))
    else:
        print("")
        print("")
        print("")

except Exception:
    print("Parse Failure")
    print("")
    print("")
    print("")
PY
}

extract_component() {
  local component="$1"

  python3 - "$component" <<'PY'
import json, sys

target = sys.argv[1].lower()

try:
    d = json.load(sys.stdin)

    for c in d.get("components", []):
        name = c.get("name", "")
        if target in name.lower():
            print(f"{name}|{c.get('status','unknown')}")
            raise SystemExit

    print(f"{target}|unknown")

except Exception:
    print(f"{target}|unknown")
PY
}

paint() {
  local payload="$1"

  local code latency body
  code="${payload%%|*}"

  local rest="${payload#*|}"
  latency="${rest%%|*}"
  body="${rest#*|}"

  local now
  now=$(date '+%H:%M:%S')

  local now_epoch
  now_epoch=$(date +%s)

  clear

  local cols
  cols=$(tput cols 2>/dev/null || echo 80)

  local banner glyph word mark

  if [[ "$code" != "200" ]]; then
    banner="\e[1;41;97m"
    glyph="💥"
    word="CLAUDE STATUS API DOWN"
    mark="🟥"
  else
    local overall
    overall=$(printf '%s' "$body" | extract_status | sed -n '1p')

    case "$overall" in
      *Operational*)
        banner="\e[1;42;97m"
        glyph="🧠"
        word="CLAUDE SYSTEMS OPERATIONAL"
        mark="🟩"
        ;;
      *Degraded*)
        banner="\e[1;43;30m"
        glyph="⚠️ "
        word="CLAUDE DEGRADED"
        mark="🟨"
        ;;
      *)
        banner="\e[1;41;97m"
        glyph="🔥"
        word="CLAUDE INCIDENT ACTIVE"
        mark="🟥"
        ;;
    esac
  fi

  HISTORY+=("$mark")

  if (( ${#HISTORY[@]} > HISTORY_MAX )); then
    HISTORY=("${HISTORY[@]: -$HISTORY_MAX}")
  fi

  local latency_ms
  latency_ms=$(printf "%.0f" "$(echo "$latency * 1000" | bc -l 2>/dev/null || echo 0)")

  LATENCY_HISTORY+=("$latency_ms")

  if (( ${#LATENCY_HISTORY[@]} > 20 )); then
    LATENCY_HISTORY=("${LATENCY_HISTORY[@]: -20}")
  fi

  local latency_info
  latency_info=$(latency_grade "$latency_ms")

  local latency_word latency_color
  IFS='|' read -r latency_word latency_color <<<"$latency_info"

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

  printf "       \e[1;97mtime:\e[0m        %s\n" "$now"
  printf "       \e[1;97mhttp:\e[0m        %s\n" "$code"
  printf "       \e[1;97mlatency:\e[0m     ${latency_color}%s (%sms)\e[0m\n" "$latency_word" "$latency_ms"

  echo

  if [[ "$code" == "200" ]]; then
    local overall incident_name incident_status incident_created

    overall=$(printf '%s' "$body" | extract_status | sed -n '1p')
    incident_name=$(printf '%s' "$body" | extract_status | sed -n '2p')
    incident_status=$(printf '%s' "$body" | extract_status | sed -n '3p')
    incident_created=$(printf '%s' "$body" | extract_status | sed -n '4p')

    printf "       \e[1;97moverall:\e[0m     %s\n" "$overall"

    if [[ -n "$incident_name" ]]; then
      echo
      printf "       \e[1;31mactive incident\e[0m\n"
      printf "       ├─ %s\n" "$incident_name"
      printf "       ├─ status: %s\n" "$incident_status"
      printf "       └─ opened: %s\n" "$incident_created"
    fi

    echo
    printf "       \e[1;97m%-24s %-18s\n" "component" "status"
    printf "       \e[2m%s\e[0m\n" "──────────────────────── ─────────────────"

    for component in "${COMPONENTS[@]}"; do
      local row
      row=$(printf '%s' "$body" | extract_component "$component")

      local cname cstatus
      IFS='|' read -r cname cstatus <<<"$row"

      local icon color

      case "$cstatus" in
        operational)
          icon="🟢"
          color="\e[1;32m"
          ;;
        degraded_performance)
          icon="🟡"
          color="\e[1;33m"
          ;;
        partial_outage)
          icon="🟠"
          color="\e[1;31m"
          ;;
        major_outage)
          icon="🔴"
          color="\e[1;41;97m"
          ;;
        *)
          icon="⚪"
          color="\e[2m"
          ;;
      esac

      printf "       %-24s ${color}%s %s\e[0m\n" \
        "$cname" "$icon" "$cstatus"
    done
  fi

  echo
  printf "       \e[1;97mhistory:\e[0m     "
  printf '%s' "${HISTORY[@]}"
  echo

  echo
  printf "       \e[2mpolling every %ss • %s attempts • ctrl-c to stop\e[0m\n" \
    "$SLEEP_BETWEEN" "$ATTEMPTS"
}

trap 'echo; echo "bye 👋"; exit 0' INT

while true; do
  payload=$(check_with_retries)
  paint "$payload"
  sleep "$SLEEP_BETWEEN"
done

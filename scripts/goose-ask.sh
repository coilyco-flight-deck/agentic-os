#!/usr/bin/env bash
# goose-ask: minimal test harness for probing the Goose harness with one-shot
# questions. Wraps `goose run --no-session`, strips the startup banner, times
# each call, and tees a raw transcript under ~/.cache/agentic-os/goose-ask/.
# See docs/test-harness-goose.md.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
goose-ask - one-shot question harness for the Goose agent.

Usage:
  goose-ask "a single question"
  goose-ask -f FILE          # one question per non-comment line, each its own run
  goose-ask -s "system text" "question"

Options:
  -f FILE    Batch file: blank lines and lines starting with # are skipped.
  -s TEXT    Extra system instructions passed to goose (--system).
  -m MODEL   Override GOOSE_MODEL for this run (e.g. qwen3:30b-a3b).
  -h         Show this help.

Each question is an independent `goose run --no-session` invocation, so no
state carries between questions. Clean answers print to stdout; full raw
output (banner, tool calls, everything) is logged under
~/.cache/agentic-os/goose-ask/<timestamp>.log.
EOF
}

batch_file=""
system_text=""
model_override=""

while getopts ":f:s:m:h" opt; do
  case "$opt" in
    f) batch_file="$OPTARG" ;;
    s) system_text="$OPTARG" ;;
    m) model_override="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) echo "goose-ask: -$OPTARG needs an argument" >&2; exit 2 ;;
    \?) echo "goose-ask: unknown option -$OPTARG" >&2; usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

if ! command -v goose >/dev/null 2>&1; then
  echo "goose-ask: goose CLI not found on PATH" >&2
  exit 127
fi

log_dir="${HOME}/.cache/agentic-os/goose-ask"
mkdir -p "$log_dir"
stamp="$(date '+%Y%m%d-%H%M%S')"
log_file="${log_dir}/${stamp}.log"

[ -n "$model_override" ] && export GOOSE_MODEL="$model_override"

# Active config, echoed once so the transcript records what was tested.
active_model="${GOOSE_MODEL:-$(sed -n 's/^GOOSE_MODEL:[[:space:]]*//p' "${HOME}/.config/goose/config.yaml" 2>/dev/null | head -n1)}"
active_host="${OLLAMA_HOST:-$(sed -n 's/^OLLAMA_HOST:[[:space:]]*//p' "${HOME}/.config/goose/config.yaml" 2>/dev/null | head -n1)}"

# Ask one question. Strips every line up to and including goose's
# "goose is ready" banner line; the answer is whatever follows.
ask_one() {
  local q="$1" start dur raw
  start=$SECONDS

  local -a cmd=(goose run --no-session -t "$q")
  [ -n "$system_text" ] && cmd+=(--system "$system_text")

  {
    echo "=== Q: $q"
    echo "=== model=${active_model:-?} host=${active_host:-?} system=${system_text:-<none>}"
  } >>"$log_file"

  raw="$("${cmd[@]}" 2>&1 || true)"
  dur=$((SECONDS - start))

  printf '%s\n' "$raw" >>"$log_file"
  echo "=== (${dur}s)" >>"$log_file"
  echo >>"$log_file"

  local answer
  answer="$(printf '%s\n' "$raw" | awk 'found{print} /goose is ready/{found=1}')"
  [ -z "$answer" ] && answer="$raw"   # banner not found: show everything

  printf '\033[1mQ:\033[0m %s\n' "$q"
  printf '%s\n' "$answer"
  printf '\033[2m   (%ss)\033[0m\n\n' "$dur"
}

echo "goose-ask: model=${active_model:-?} host=${active_host:-?}"
echo "goose-ask: log -> $log_file"
echo

if [ -n "$batch_file" ]; then
  [ -r "$batch_file" ] || { echo "goose-ask: cannot read $batch_file" >&2; exit 1; }
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ''|'#'*) continue ;;
    esac
    ask_one "$line"
  done <"$batch_file"
elif [ "$#" -gt 0 ]; then
  ask_one "$*"
else
  usage
  exit 2
fi

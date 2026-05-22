#!/usr/bin/env bash
# Decorate this agent's self-name for the Claude Code status line or the
# SessionStart hook.
#
# The name follows the scheme claude-<os>-<hostname>-<tag>. coily is the
# single source of truth: when `coily agent-name` is available this script
# defers to it. The local computation below is a fallback for hosts without
# coily, or running a coily too old to know the verb.
#
# Argument 1 picks the flavor: "statusline" (default) or "sessionstart".
set -euo pipefail

mode="${1:-statusline}"

# session_id arrives in the statusLine / SessionStart JSON payload on stdin.
payload="$(cat | tr -d '\n')"
sid="$(printf '%s' "$payload" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"

# local_name mirrors `coily agent-name`, for hosts without coily.
local_name() {
  local os host tag
  case "$(uname -s)" in
    Darwin)               os=macos ;;
    Linux)                os=linux ;;
    MINGW* | MSYS* | CYGWIN*) os=windows ;;
    *)                    os="$(uname -s | tr '[:upper:]' '[:lower:]')" ;;
  esac
  host="$(hostname -s 2>/dev/null || hostname)"
  host="$(printf '%s' "$host" | tr '[:upper:]' '[:lower:]' | cut -d. -f1)"
  tag="$(printf '%s' "$sid" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9' | tail -c 4)"
  printf 'claude-%s-%s' "$os" "$host"
  [ -n "$tag" ] && printf -- '-%s' "$tag"
}

# The name is stable per session; cache it so the status line does not
# spawn coily on every refresh.
cache="${TMPDIR:-/tmp}/agent-name-${sid:-nosession}"
if [ -s "$cache" ]; then
  name="$(cat "$cache")"
else
  name=""
  if command -v coily >/dev/null 2>&1; then
    name="$(coily agent-name --session-id "$sid" 2>/dev/null | head -n1 || true)"
  fi
  # Accept only a well-formed name; otherwise fall back to local compute.
  # A valid name is lowercase claude-<...> with no spaces or other chars.
  if [[ "$name" != claude-* || "$name" == *[^a-z0-9-]* ]]; then
    name="$(local_name)"
  fi
  printf '%s' "$name" >"$cache"
fi

case "$mode" in
  sessionstart)
    printf '🐾 You are %s this session. When asked "who are you" or "what is your status", lead with this name.\n' "$name"
    ;;
  statusline | *)
    printf '%s - your agent this session' "$name"
    ;;
esac

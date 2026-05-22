#!/usr/bin/env bash
# Print this agent's self-name for the Claude Code status line or the
# SessionStart hook. See README.md "Agent self-name" for the scheme.
#
#   claude-<os>-<hostname>-<tag>
#
# <os> is the friendly slug (macos / windows / linux), <hostname> is the
# short hostname, <tag> is the last 4 alphanumeric chars of the session id.
# Argument 1 picks the output flavor: "statusline" (default) or "sessionstart".
set -euo pipefail

mode="${1:-statusline}"

# session_id arrives in the statusLine / SessionStart JSON payload on stdin.
payload="$(cat | tr -d '\n')"
sid="$(printf '%s' "$payload" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
tag="$(printf '%s' "$sid" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9' | tail -c 4)"

case "$(uname -s)" in
  Darwin)              os=macos ;;
  Linux)               os=linux ;;
  MINGW*|MSYS*|CYGWIN*) os=windows ;;
  *)                   os="$(uname -s | tr '[:upper:]' '[:lower:]')" ;;
esac

host="$(hostname -s 2>/dev/null || hostname)"
host="$(printf '%s' "$host" | tr '[:upper:]' '[:lower:]' | cut -d. -f1)"

name="claude-${os}-${host}"
[ -n "$tag" ] && name="${name}-${tag}"

case "$mode" in
  sessionstart)
    printf '🐾 You are %s this session - Claude running on %s, host %s. When asked "who are you" or "what is your status", lead with this name.\n' \
      "$name" "$os" "$host"
    ;;
  statusline | *)
    printf '%s - your agent this session' "$name"
    ;;
esac

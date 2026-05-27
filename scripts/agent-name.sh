#!/usr/bin/env bash
# Decorate this agent's self-name. See docs/agent-name.md.
set -euo pipefail

mode="${1:-statusline}"

payload="$(cat | tr -d '\n')"
sid="$(printf '%s' "$payload" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"

# Fallback for hosts without coily.
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

# Stable per session, cached to avoid spawning coily on every status-line refresh.
cache="${TMPDIR:-/tmp}/agent-name-${sid:-nosession}"
if [ -s "$cache" ]; then
  name="$(cat "$cache")"
else
  name=""
  if command -v coily >/dev/null 2>&1; then
    name="$(coily agent-name --session-id "$sid" 2>/dev/null | head -n1 || true)"
  fi
  # Accept only well-formed names; fall back to local compute otherwise.
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

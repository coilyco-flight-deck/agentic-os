#!/usr/bin/env bash
# Decorate this agent's self-name. See docs/agent-name.md.
set -euo pipefail

mode="${1:-statusline}"

payload="$(cat)"
payload_flat="$(printf '%s' "$payload" | tr -d '\n')"
sid="$(printf '%s' "$payload_flat" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
transcript="$(printf '%s' "$payload_flat" \
  | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
model_id="$(printf '%s' "$payload_flat" \
  | sed -n 's/.*"model"[[:space:]]*:[[:space:]]*{[^}]*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"

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
  sid_lc="$(printf '%s' "$sid" | tr '[:upper:]' '[:lower:]')"
  letters="$(printf '%s' "$sid_lc" | tr -cd 'a-z' | cut -c1-2)"
  digits="$(printf '%s' "$sid_lc" | tr -cd '0-9' | cut -c1-2)"
  tag="${letters}${digits}"
  printf 'claude-%s-%s' "$os" "$host"
  [ -n "$tag" ] && printf -- '-%s' "$tag"
  # Pronoun slug. The local fallback is claude-only, so always she-her.
  # coily emits he-him / they-them for codex / openclaw.
  printf -- '-she-her'
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

# Context-usage snippet from the transcript's last assistant message.
# Format: " | ctx 132k/1M (13%) out 4.2k". Empty on any failure.
ctx_snippet() {
  [ -n "$transcript" ] && [ -r "$transcript" ] || return 0
  python3 - "$transcript" <<'PY' 2>/dev/null || true
import json, sys
path = sys.argv[1]
# Soft budget. 250k = failure case per Kai. Progressive bands below.
BUDGET = 250_000
last_in = last_cr = last_crd = 0
total_out = 0
try:
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            msg = d.get("message")
            if not isinstance(msg, dict):
                continue
            u = msg.get("usage")
            if not isinstance(u, dict):
                continue
            total_out += int(u.get("output_tokens") or 0)
            if msg.get("role") == "assistant":
                last_in = int(u.get("input_tokens") or 0)
                last_cr = int(u.get("cache_read_input_tokens") or 0)
                last_crd = int(u.get("cache_creation_input_tokens") or 0)
except Exception:
    sys.exit(0)
ctx = last_in + last_cr + last_crd
if ctx == 0 and total_out == 0:
    sys.exit(0)
def k(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1000:.1f}k"
    return str(n)
pct = 100 * ctx / BUDGET
# ANSI color bands. <50% green, 50-75% yellow, 75-100% bright-orange,
# >=100% bright-red bold blink.
if pct < 50:
    color, label = "\033[32m", "ok"     # green
elif pct < 75:
    color, label = "\033[33m", "warn"   # yellow
elif pct < 100:
    color, label = "\033[38;5;208m", "hot"  # 256-color orange
else:
    color, label = "\033[1;5;91m", "OVER"   # bold blink bright red
reset = "\033[0m"
print(f" | {color}ctx {k(ctx)}/250k ({pct:.0f}% {label}){reset} out {k(total_out)}", end="")
PY
}

# Human-readable pronouns parsed from the name's trailing slug, so this works
# for coily-provided codex/openclaw names too, not just the claude fallback.
pronoun_display() {
  case "$1" in
    *-she-her)   printf 'she/her' ;;
    *-he-him)    printf 'he/him' ;;
    *-they-them) printf 'they/them' ;;
  esac
}
pronouns="$(pronoun_display "$name")"

case "$mode" in
  sessionstart)
    printf '🐾 You are %s%s this session. When asked "who are you" or "what is your status", lead with this name.\n' "$name" "${pronouns:+ ($pronouns)}"
    ;;
  statusline | *)
    printf '%s - your agent this session%s' "$name" "$(ctx_snippet)"
    ;;
esac

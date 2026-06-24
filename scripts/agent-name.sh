#!/usr/bin/env bash
# Decorate this agent's self-name. See docs/features-agents-sessions.md.
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
# Claude Code passes the project root via workspace.project_dir (preferred) or
# cwd. Fall back to $CLAUDE_PROJECT_DIR / $PWD only if both are absent.
project_dir="$(printf '%s' "$payload_flat" \
  | sed -n 's/.*"workspace"[[:space:]]*:[[:space:]]*{[^}]*"project_dir"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
[ -z "$project_dir" ] && project_dir="$(printf '%s' "$payload_flat" \
  | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
[ -z "$project_dir" ] && project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"

# Harness registry (prefix = harness name, value = pronoun slug). Pick the
# harness via AOS_AGENT_HARNESS, default claude. See docs/features-agents-sessions.md.
harness="${AOS_AGENT_HARNESS:-claude}"
pronoun_slug_for() {
  case "$1" in
    claude)   printf 'she-her' ;;
    codex)    printf 'he-him' ;;
    opencode) printf 'they-them' ;;
    aider)    printf 'they-them' ;;
    goose)    printf 'she-her' ;;
    *)        printf 'she-her' ;; # unknown harness: default she-her
  esac
}

# Compute the name locally (harness-aware via the registry). Authoritative
# today: the `ward agent-name` override below is not yet implemented.
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
  printf '%s-%s-%s' "$harness" "$os" "$host"
  [ -n "$tag" ] && printf -- '-%s' "$tag"
  printf -- '-%s' "$(pronoun_slug_for "$harness")"
}

# Stable per session, cached to avoid spawning ward on every status-line
# refresh. Key on harness too, so two harnesses never share a cached name.
cache="${TMPDIR:-/tmp}/agent-name-${harness}-${sid:-nosession}"
if [ -s "$cache" ]; then
  name="$(cat "$cache")"
else
  name=""
  # Optional future override: if ward ever ships `agent-name`, prefer it.
  if command -v ward >/dev/null 2>&1; then
    name="$(ward agent-name --session-id "$sid" 2>/dev/null | head -n1 || true)"
  fi
  # Accept only a well-formed name for this harness; else compute locally.
  if [[ "$name" != "$harness"-* || "$name" == *[^a-z0-9-]* ]]; then
    name="$(local_name)"
  fi
  printf '%s' "$name" >"$cache"
fi

# Context-usage snippet from the transcript's last assistant message.
# Format: "  ctx 132k/250k (13% ok)". Empty on any failure.
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
print(f"  {color}ctx {k(ctx)}/250k ({pct:.0f}% {label}){reset}", end="")
PY
}

# Human-readable pronouns parsed from the name's trailing slug, so this works
# for ward-provided codex/opencode names too, not just the claude fallback.
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
    printf '%s%s' "$name" "$(ctx_snippet)"
    # Second row, project-local: $project_dir/.agentic-os/statusline.sh.
    project_hook="$project_dir/.agentic-os/statusline.sh"
    if [ -x "$project_hook" ]; then
      hook_out="$("$project_hook" 2>/dev/null)"
      [ -n "$hook_out" ] && printf '\n%s' "$hook_out"
    fi
    # Second row: $AGENT_STATUSLINE_EXTRA. See docs/features-agents-sessions.md.
    extra_cmd="${AGENT_STATUSLINE_EXTRA:-}"
    if [ -n "$extra_cmd" ] && [ -x "$extra_cmd" ]; then
      extra="$("$extra_cmd" 2>/dev/null || true)"
      [ -n "$extra" ] && printf '\n%s' "$extra"
    fi
    ;;
esac

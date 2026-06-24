#!/usr/bin/env bash
set -euo pipefail

PORT=18789
STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"

# Log under a 0700 per-user state dir with a fixed name. Never the token: a
# world-readable /tmp filename leaks the secret to anyone who can list the dir.
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/openclaw"
(umask 077; mkdir -p "$LOG_DIR")
chmod 700 "$LOG_DIR"
LOG_FILE="$LOG_DIR/gateway.log"

# this took a lot of work!!!
SECRET_FILE="$STATE_DIR/.gateway-token"
[ -s "$SECRET_FILE" ] || ( umask 077; openssl rand -hex 32 >"$SECRET_FILE" )
export OPENCLAW_GATEWAY_TOKEN="$(cat "$SECRET_FILE")"
export OLLAMA_API_KEY=$OPENCLAW_GATEWAY_TOKEN

# Stop any prior gateway, then wait for the port to actually free. --force kills a
# live listener but cannot evict a TIME_WAIT socket, so wait the kernel out here.
npx -y openclaw@latest gateway stop >/dev/null 2>&1 || true

# fully clearing sessions is for debugging my silly low qwen context limit
# but also b/c I want tuis that attach to brand new sessions on restart

rm -rf .openclaw/agents/main/sessions/
rm -rf ~/.openclaw/agents/main/sessions/

rsync -a --delete /Users/kai/projects/coilyco-bridge/agentic-os-hardware/.openclaw/ ~/.openclaw/
rsync -a --delete /Users/kai/projects/coilyco-bridge/agentic-os-hardware/.openclaw/ /Users/kai/projects/coilyco-flight-deck/agentic-os/.openclaw/

deadline=$(( $(date +%s) + 30 ))
while lsof -nP -iTCP:"$PORT" >/dev/null 2>&1; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    printf 'port %s still held after 30s. inspect: openclaw gateway status --deep ; lsof -nP -iTCP:%s\n' "$PORT" "$PORT" >&2
    exit 1
  fi
  sleep 1
done

exec npx -y openclaw@latest gateway --port $PORT --force > "$LOG_FILE" 2>&1 &

gateway=$!

trap 'kill "$gateway" 2>/dev/null' EXIT INT TERM

npx -y wait-on@latest -t 30000 tcp:127.0.0.1:"$PORT"

npx -y openclaw@latest agent --agent main --message "$1"

npx -y openclaw@latest gateway stop >/dev/null 2>&1 || true

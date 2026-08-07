#!/usr/bin/env bash
# Stop hook: block when the final assistant message uses an issue/PR hash-ref
# (owner/repo#N or bare #NN) and ask for a rewrite to the full Forgejo URL.

# Post org-migration the hash-ref is ambiguous (coilysiren now redirects) and
# breaks tooling. Canonical: https://forgejo.coilysiren.me/<owner>/<repo>/issues/<N>

# Wired into ~/.claude/settings.json hooks.Stop by the claude-hooks ansible
# role; reads Stop event JSON on stdin. Disable by removing that block or
# `chmod -x`. Origin: agentic-os-kai issues 551 and 847.
set -uo pipefail

# Entry-time debug log (agentic-os-kai issue 682): "never fired" vs "fired and
# passed". One line per Stop. CHECK_ISSUE_REFS_LOG overrides it; /dev/null mutes.
log_file="${CHECK_ISSUE_REFS_LOG:-${HOME:-/tmp}/.claude/check-issue-refs.log}"
log() {
  { mkdir -p "$(dirname "$log_file")" 2>/dev/null \
      && printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$log_file"; } 2>/dev/null || true
}

input=$(cat)
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null || true)
active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null || true)
log "enter transcript=${transcript:-<none>} stop_hook_active=${active}"

# Loop guard: already blocked once in this stop sequence. Let it through so an
# unfixable message (e.g. one quoting the hash-ref convention) cannot trap it.
if [ "$active" = "true" ]; then log "pass: loop-guard (stop_hook_active)"; exit 0; fi
if [ -z "$transcript" ] || [ ! -f "$transcript" ]; then log "pass: no transcript"; exit 0; fi

# Final assistant TURN text: every `text` block after the last user record (the
# old `| last` form hit one record, often non-text on real transcripts; iss 682).
msg=$(jq -rs '
  [ .[] ] as $a
  | ([ $a | to_entries[] | select(.value.type=="user") | .key ] | last // -1) as $lu
  | [ $a[($lu + 1):][]
      | select(.type=="assistant")
      | (.message.content // [])
      | if type=="array" then (.[] | select(.type=="text") | .text)
        else tostring end ]
  | join("\n")
' "$transcript" 2>/dev/null || true)
if [ -z "$msg" ]; then log "pass: empty final-turn text"; exit 0; fi

# Drop fenced code blocks and inline code so patterns shown as examples,
# CSS hex (#abc), and "#define"-style code don't trip the check.
clean=$(printf '%s\n' "$msg" | sed -e '/^[[:space:]]*```/,/^[[:space:]]*```/d' -e 's/`[^`]*`//g')

# owner/repo#N (issue/PR ref) OR bare #NN (>=2 digits, skips prose like "step
# #1"). Full Forgejo URLs never match: /issues/NNN has no '#'.
if printf '%s' "$clean" | grep -qE '([A-Za-z0-9._-]+/[A-Za-z0-9._-]+#[0-9]+)|((^|[^[:alnum:]&#])#[0-9]{2,})'; then
  reason="Your reply referenced an issue/PR with a hash-ref (owner/repo#N or a bare #NN). Post org-migration that short form is ambiguous and breaks tooling. Rewrite EVERY such reference as a fully-qualified canonical Forgejo URL: https://forgejo.coilysiren.me/<owner>/<repo>/issues/<N> (canonical owner is coilyco-bridge or coilyco-flight-deck, not coilysiren). Then resend the corrected message. (If the ref only appears inside a code block or inline-code, ignore this.)"
  log "block: hash-ref in final turn"
  jq -nc --arg r "$reason" '{decision:"block", reason:$r}'
  exit 0
fi
log "pass: no hash-ref in final turn"
exit 0

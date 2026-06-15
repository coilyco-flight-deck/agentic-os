#!/usr/bin/env sh
# SessionStart hook: keep the composed agent-context load points fresh.
#
# Editing a source AGENTS.md has no trigger of its own - only an ansible
# converge recomposes COMPOSED.<harness>.md. So an edit can sit unsynced at the
# user-level load point until the next converge, and a wrong source entry can
# freeze it silently. This hook closes that gap: on every session start it runs
# the composer, which rewrites only when content actually changed (silent no-op
# otherwise) and prints a one-line warning for any source it had to skip. Its
# stdout becomes session context, so a stale or misconfigured load point is
# loud at the point of use instead of scrolling past in converge output.
#
# Opt-in and provider-agnostic: no config -> no-op. Never blocks a session.
set -u

config="${HOME}/.config/agent-compose/agent-compose.yaml"
[ -r "$config" ] || exit 0

# scripts/ lives at the agentic-os repo root; its parent is the PYTHONPATH root.
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
aos_root=$(dirname -- "$script_dir")

PYTHONPATH="$aos_root" python3 -m agentic_os.generators.generate_agent_compose 2>&1 || true
exit 0

#!/usr/bin/env bash

set -euo pipefail

aosguard --version
test -s /opt/agentic-os/aosguard-skill/aosguard/SKILL.md
test -s /opt/agentic-os/aosguard-skill/aosguard/references/commands.yaml

roster_dir="$(mktemp -d)"
trap 'rm -rf "$roster_dir"' EXIT
agent-compose version
agent-compose roster --out "$roster_dir"
jq -e \
  '.source == "person:kai" and (.role_order | length > 0) and (.personalities | length > 0)' \
  "$roster_dir/person.json" >/dev/null
test -s "$roster_dir/AGENTS.COMPOSE.md"
test -n "$(find "$roster_dir/personalities" -type f -name '*.md' -print -quit)"

python3 -m agentic_os.forgejo_actions_list --help >/dev/null
ward --version
CLIGUARD_NO_SANDBOX=1 WARD_DOCTOR_ALLOW_PLACEHOLDERS=1 ward doctor

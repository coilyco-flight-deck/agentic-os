#!/usr/bin/env sh
# SessionStart hook: cat a cached orientation blob if one exists, else no-op.
# Contract: a producer writes YAML to ~/.cache/agentic-os/session-pulse.yaml.
set -u

pulse="${HOME}/.cache/agentic-os/session-pulse.yaml"
[ -r "$pulse" ] || exit 0
cat "$pulse"

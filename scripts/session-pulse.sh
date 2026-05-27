#!/usr/bin/env sh
# SessionStart hook: surface a cached orientation blob if one exists.
# Contract: any producer writes YAML to ~/.cache/agentic-os/session-pulse.yaml.
# Zero compute here. Missing file is a clean no-op.
set -u

pulse="${HOME}/.cache/agentic-os/session-pulse.yaml"
[ -r "$pulse" ] || exit 0
cat "$pulse"

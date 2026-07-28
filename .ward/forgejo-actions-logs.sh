#!/usr/bin/env bash
# Temporary attribution rollover marker for agentic-os#773.
set -euo pipefail

exec python3 -m agentic_os.forgejo_actions_logs "$@"

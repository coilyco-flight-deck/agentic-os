#!/usr/bin/env bash
# Status-line provider: the agent self-name row. See docs/statusline.md.
#
# Thin shim - the canonical <harness>-<os>-<host>-<tag>-<pronouns> derivation
# lives in the sibling agent-name.sh (also the sessionstart / gitidentity hook
# target), so this provider just delegates to its statusline mode rather than
# duplicate the registry. The composer exports AOS_STATUSLINE_HOME to the dir
# holding both scripts; fall back to the baked /opt path.
set -euo pipefail

home="${AOS_STATUSLINE_HOME:-/opt/agentic-os}"
exec "$home/agent-name.sh" statusline

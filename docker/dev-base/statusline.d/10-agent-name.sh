#!/usr/bin/env bash
# Status-line provider: the agent self-name row. See docs/statusline.md.
#
# Thin shim - the canonical <harness>-<os>-<host>-<tag>-<pronouns> derivation
# lives in the sibling agent-name.sh (also the sessionstart / gitidentity hook
# target), so this provider just delegates to its statusline mode rather than
# duplicate the registry. The composer exports AOS_STATUSLINE_HOME. In the
# image it holds both scripts, while a host checkout keeps the canonical script
# under scripts/.
set -euo pipefail

home="${AOS_STATUSLINE_HOME:-/opt/agentic-os}"
script="$home/agent-name.sh"
if [ ! -x "$script" ]; then
  script="$home/../../scripts/agent-name.sh"
fi
[ -x "$script" ] || exit 0
exec "$script" statusline

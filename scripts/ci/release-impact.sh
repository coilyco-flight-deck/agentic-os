#!/usr/bin/env bash
# Bridge a Forgejo event to the repository-owned artifact impact classifier.
set -euo pipefail

surface=${1:?release surface is required}
event_name=${2:?event name is required}
base=${3:-}
head=${4:-HEAD}

if [ "$event_name" = "workflow_dispatch" ]; then
  uv run python -m agentic_os.release_impact \
    --surface "$surface" \
    --force \
    --github-output "$GITHUB_OUTPUT"
else
  uv run python -m agentic_os.release_impact \
    --surface "$surface" \
    --base "$base" \
    --head "$head" \
    --github-output "$GITHUB_OUTPUT"
fi

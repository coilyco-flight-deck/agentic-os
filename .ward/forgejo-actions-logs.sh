#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
    echo "usage: actions logs <owner> <repo> <run-index> <job-index> <attempt>" >&2
    exit 64
fi

if [[ -z "${FORGEJO_TOKEN:-}" ]]; then
    echo "FORGEJO_TOKEN is required" >&2
    exit 1
fi

owner=$1
repo=$2
run_index=$3
job_index=$4
attempt=$5

base_url="${FORGEJO_BASE_URL:-https://forgejo.coilysiren.me}"
url="${base_url}/api/v1/repos/${owner}/${repo}/actions/runs/${run_index}/jobs/${job_index}/attempt/${attempt}/logs"

curl -fsSL \
    -H "Authorization: token ${FORGEJO_TOKEN}" \
    -H "Accept: text/plain" \
    "$url"

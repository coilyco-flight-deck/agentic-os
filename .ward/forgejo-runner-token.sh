#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "usage: generate-runner-token global | org <org> | repo <owner> <repo>" >&2
    exit 64
}

if [[ $# -lt 1 ]]; then
    usage
fi

scope=$1
shift

if [[ -z "${FORGEJO_TOKEN:-}" ]]; then
    echo "FORGEJO_TOKEN is required" >&2
    exit 1
fi

case "$scope" in
    global)
        [[ $# -eq 0 ]] || usage
        path="admin/runners/registration-token"
        ;;
    org)
        [[ $# -eq 1 ]] || usage
        path="orgs/$1/actions/runners/registration-token"
        ;;
    repo)
        [[ $# -eq 2 ]] || usage
        path="repos/$1/$2/actions/runners/registration-token"
        ;;
    *)
        usage
        ;;
esac

base_url="${FORGEJO_BASE_URL:-https://forgejo.coilysiren.me}"

curl -fsSL \
    -H "Authorization: token ${FORGEJO_TOKEN}" \
    -H "Accept: application/json" \
    "${base_url}/api/v1/${path}"

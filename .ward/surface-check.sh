#!/usr/bin/env bash
# Surface capability self-check (agentic-os#447). Asserts a live ward surface
# carries every capability its role tier promises (docs/role-surface-tiers.md),
# so an over-broad permissions rollback fails loud at bring-up instead of being
# discovered by hand mid-incident. Read-only: probes binaries, creds, daemons,
# and mounted ward verbs, then exits non-zero listing every missing capability.
# Usage: surface-check.sh [role]  (defaults to $WARD_ROLE)
set -uo pipefail

role="${1:-${WARD_ROLE:-}}"
if [[ -z "$role" ]]; then
    echo "usage: surface-check.sh [role] (or set WARD_ROLE)" >&2
    exit 64
fi

failures=()

need_binary() {
    command -v "$1" >/dev/null 2>&1 || failures+=("binary: $1 not on PATH")
}

need_forgejo_token() {
    if [[ -z "${FORGEJO_TOKEN:-}" ]]; then
        failures+=("creds: FORGEJO_TOKEN not set")
    fi
}

need_aws() {
    need_binary aws
    if [[ ! -d "${HOME}/.aws" && -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
        failures+=("creds: no ~/.aws dir and no AWS_ACCESS_KEY_ID in env")
    fi
}

need_tailnet() {
    need_binary tailscale
    if command -v tailscale >/dev/null 2>&1 \
        && ! tailscale status >/dev/null 2>&1; then
        failures+=("tailnet: tailscale status failed (tailscaled down or logged out)")
    fi
}

need_kubectl() {
    need_binary kubectl
    if [[ ! -f "${KUBECONFIG:-${HOME}/.kube/config}" ]]; then
        failures+=("creds: no kubeconfig at \${KUBECONFIG:-~/.kube/config}")
    fi
}

need_runner_token_verb() {
    if ! ward ops forgejo actions --help 2>/dev/null \
        | grep -q "generate-runner-token"; then
        failures+=("verb: ward ops forgejo actions generate-runner-token not mounted")
    fi
}

need_binary ward
need_binary git

case "$role" in
    engineer | qa)
        need_forgejo_token
        ;;
    advisor)
        need_forgejo_token
        need_aws
        need_tailnet
        ;;
    director | ops)
        need_forgejo_token
        need_aws
        need_tailnet
        need_kubectl
        need_runner_token_verb
        ;;
    *)
        echo "surface-check: unknown role '$role' (see docs/role-surface-tiers.md)" >&2
        exit 64
        ;;
esac

if [[ ${#failures[@]} -gt 0 ]]; then
    echo "surface-check: role '$role' is missing ${#failures[@]} expected capabilities:" >&2
    printf ' - %s\n' "${failures[@]}" >&2
    echo "expected tier: docs/role-surface-tiers.md - this is drift, fix the surface" >&2
    exit 1
fi

echo "surface-check: role '$role' surface matches its tier"

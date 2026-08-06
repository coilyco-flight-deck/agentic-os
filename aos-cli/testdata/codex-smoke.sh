#!/bin/sh
set -eu

config="${CODEX_HOME:?}/config.toml"
workspace="$(pwd)"

if [ ! -f "${config}" ]; then
    echo "Codex smoke: missing config at ${config}" >&2
    exit 1
fi
for expected in \
    'approval_policy = "never"' \
    'sandbox_mode = "danger-full-access"' \
    '[notice]' \
    'hide_rate_limit_model_nudge = true' \
    "[projects.\"${workspace}\"]" \
    'trust_level = "trusted"'; do
    if ! rg -Fqx "${expected}" "${config}"; then
        echo "Codex smoke: config omits ${expected}" >&2
        exit 1
    fi
done
if rg -q '^model =' "${config}"; then
    echo "Codex smoke: AOS must leave model unset" >&2
    exit 1
fi
if rg -q '^model_reasoning_effort =' "${config}"; then
    echo "Codex smoke: AOS must leave reasoning effort unset" >&2
    exit 1
fi
if rg -q '^model_verbosity =' "${config}"; then
    echo "Codex smoke: AOS must leave model verbosity unset" >&2
    exit 1
fi

go test ./...
codex --strict-config --version

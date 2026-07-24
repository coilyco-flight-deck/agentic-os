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
    "[projects.\"${workspace}\"]" \
    'trust_level = "trusted"'; do
    if ! rg -Fqx "${expected}" "${config}"; then
        echo "Codex smoke: config omits ${expected}" >&2
        exit 1
    fi
done
if rg -q '^(model|model_reasoning_effort|model_verbosity) =' "${config}"; then
    echo "Codex smoke: AOS must leave model selection unset" >&2
    exit 1
fi

go test ./...
codex --strict-config --version

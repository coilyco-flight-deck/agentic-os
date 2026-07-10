#!/usr/bin/env bash
# Seed the canonical aos checkout before the director shell starts. Read-only
# container surfaces skip host rc files, so this wrapper restores the env from
# the checkout that built the image rather than whatever cwd a child command
# happens to use later.

set -u

for _siren_aos_root in \
  /workspace/coilyco-flight-deck/agentic-os \
  /workspace/agentic-os \
  "$HOME/projects/coilyco-flight-deck/agentic-os"; do
  if git -C "$_siren_aos_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    export AOS_REPO_ROOT="$_siren_aos_root"
    export WARD_CONFIG_REF="forgejo.coilysiren.me/coilyco-flight-deck/agentic-os@$(git -C "$_siren_aos_root" rev-parse HEAD)//.ward"
    break
  fi
done

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec "${SHELL:-/bin/bash}"

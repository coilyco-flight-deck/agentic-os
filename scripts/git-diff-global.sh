#!/usr/bin/env bash
# Enumerate dirty repos under ~/projects/coilysiren/*. See docs/git-diff-global.md.

set -euo pipefail

mode="${1:-status}"
root="${COILYSIREN_ROOT:-$HOME/projects/coilysiren}"

shopt -s nullglob
any=0
for d in "$root"/*/.git; do
  r=${d%/.git}
  name=${r##*/}

  case "$mode" in
    --stat) body=$(git -C "$r" diff --stat; git -C "$r" diff --cached --stat) ;;
    --full) body=$(git -C "$r" diff; git -C "$r" diff --cached) ;;
    *)      body=$(git -C "$r" status --porcelain) ;;
  esac

  [ -z "$body" ] && continue
  any=1
  echo "== $name =="
  echo "$body"
  echo
done

[ "$any" -eq 0 ] && echo "all clean under $root"
exit 0

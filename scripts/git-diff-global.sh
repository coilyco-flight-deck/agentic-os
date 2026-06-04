#!/usr/bin/env bash
# Enumerate dirty repos across every git working tree, two levels deep under
# ~/projects/<org>/*. Override the root with $PROJECTS_ROOT. See agentic-os-kai#560.

set -euo pipefail

mode="${1:-status}"
root="${PROJECTS_ROOT:-$HOME/projects}"

# Collect repo working trees. A $root child carrying .git is itself a repo
# (single-org-root layout), otherwise it is an org dir holding the repos.
shopt -s nullglob
repos=()
for child in "$root"/*/; do
  child=${child%/}
  if [ -e "$child/.git" ]; then
    repos+=("$child")
  else
    for r in "$child"/*/; do
      r=${r%/}
      [ -e "$r/.git" ] && repos+=("$r")
    done
  fi
done

any=0
# ${arr[@]+...} guard: empty-array expansion under `set -u` is an error on
# bash 3.2 (the macOS default).
for r in ${repos[@]+"${repos[@]}"}; do
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

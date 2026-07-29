#!/usr/bin/env bash
# Offline secret scan for the catalog pre-commit suite. See agentic-os#288.
#
# Wraps `trufflehog git file://.` with a path-exclude list so a trufflehog build
# that walks untracked working-tree files (its git source reads gitignored dirs
# like Rust `target/`, upstream trufflesecurity/trufflehog) cannot drown the
# scan in build-artifact false positives and block every commit fleet-wide.
#
# --exclude-paths (a regex file) is load-bearing over the inline --exclude-globs:
# only exclude-paths filters the git source's synthetic working/staged diff by
# path. --exclude-globs filters committed git-log objects alone, so it does NOT
# suppress the untracked-file read that causes the block (verified empirically,
# agentic-os#288). The regex set mirrors agentic-os-kai's CI trufflehog scan.
#
# Real staged-secret detection is untouched: only conventionally-gitignored
# build/cache dirs are excluded, and a secret anywhere else still fails the scan.

exclude_paths_file="$(mktemp)"
cleanup() {
  rm -f "$exclude_paths_file"
}
trap cleanup EXIT

cat >"$exclude_paths_file" <<'EOF'
(^|/)target/
(^|/)\.venv/
(^|/)venv/
(^|/)node_modules/
(^|/)__pycache__/
(^|/)\.mypy_cache/
(^|/)\.pytest_cache/
(^|/)\.ruff_cache/
(^|/)(dist|build)/
EOF

# Git Bash creates a POSIX-style /tmp path, while the native Windows
# trufflehog binary needs the equivalent Windows path.
trufflehog_exclude_paths="$exclude_paths_file"
if command -v cygpath >/dev/null 2>&1; then
  trufflehog_exclude_paths="$(cygpath -w "$exclude_paths_file")"
fi

trufflehog git file://. --since-commit HEAD \
  --exclude-paths "$trufflehog_exclude_paths" \
  --no-verification --no-update --fail

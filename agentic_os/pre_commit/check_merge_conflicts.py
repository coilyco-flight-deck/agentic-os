#!/usr/bin/env python3
"""Reject staged files that still carry merge-conflict markers.

A conflicted file committed verbatim is a latent break: conflict markers
(`<<<<<<<`, `=======`, `>>>>>>>`, and the diff3 base `|||||||`) are not valid
in any source language, so a script-style file silently fails at its next
invocation. This bites hardest in security-config files like
`.claude/lockdown-deny.sh`, where a broken script degrades to fail-open.
See coilyco-flight-deck/agentic-os#39.

File discovery mirrors the rest of the suite: with staged changes present
the index blobs are scanned (exactly what the commit would record); with
nothing staged (e.g. `pre-commit run --all-files`) every tracked file in
the working tree is scanned instead. Opt paths out via
`[tool.agentic-os.merge-conflicts] excludes = [...]` in pyproject.toml.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from agentic_os.config import is_enabled, is_excluded, load_excludes

REPO_ROOT = Path.cwd()
HOOK_ID = "merge-conflicts"

# Markers that open/close a conflict hunk carry a trailing space then a label
# (`<<<<<<< HEAD`); the separator line is exactly seven equals. Match both.
PREFIX_MARKERS = ("<<<<<<< ", ">>>>>>> ", "||||||| ")
SEPARATOR = "======="


def _git_lines(args: list[str]) -> list[str]:
    """Run a git command, returning NUL-split nonempty tokens (or [])."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return []
    return [tok for tok in out.split("\0") if tok]


def staged_files() -> list[str]:
    """Repo-relative paths staged for commit (added/copied/modified/renamed)."""
    return _git_lines(
        ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
    )


def tracked_files() -> list[str]:
    """Every tracked path, used as the `--all-files` fallback."""
    return _git_lines(["ls-files", "-z"])


def _staged_blob(rel: str) -> str | None:
    """The staged (index) content of `rel`, or None if unreadable as text."""
    try:
        raw = subprocess.run(
            ["git", "show", f":{rel}"],
            capture_output=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _working_text(rel: str) -> str | None:
    """The working-tree content of `rel`, or None if unreadable as text."""
    try:
        return (REPO_ROOT / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def scan(rel: str, text: str) -> list[str]:
    """Return `rel:line` hits for every conflict-marker line in `text`."""
    hits: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        body = line.rstrip("\r")
        if body.startswith(PREFIX_MARKERS) or body == SEPARATOR:
            hits.append(f"{rel}:{line_no}: {body[:40]}")
    return hits


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    excludes = load_excludes(HOOK_ID)
    staged = staged_files()
    if staged:
        files, reader = staged, _staged_blob
    else:
        files, reader = tracked_files(), _working_text

    violations: list[str] = []
    for rel in files:
        if is_excluded(rel, excludes):
            continue
        text = reader(rel)
        if text is None:
            continue
        violations.extend(scan(rel, text))

    if not violations:
        print("merge-conflicts check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(
        f"\n{len(violations)} merge-conflict marker(s) found. Resolve the "
        f"conflict and restage before committing.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

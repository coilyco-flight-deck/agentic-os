#!/usr/bin/env python3
"""Reject direct issue references in tracked text files.

This hook ships staged, not fleet-on. Repos opt in explicitly when they are
ready to replace issue-thread anchors with durable documentation links.
"""
from __future__ import annotations

import re
import sys

from agentic_os.config import has_hook_config, is_enabled, is_excluded, load_excludes, load_str_list
from agentic_os.pre_commit.text_scan import read_text, scan_text, target_files

HOOK_ID = "issue-reference-guard"
SKIP_FILES = {"pyproject.toml", ".agentic-os.toml"}

RULES = [
    (
        "bare-issue-ref",
        re.compile(r"(?<![\w/.-])#\d+\b"),
        "replace bare issue refs with durable docs or stable links",
    ),
    (
        "scoped-issue-ref",
        re.compile(r"(?<![\w.-])[\w.-]+/[\w.-]+#\d+\b"),
        "replace scoped issue refs with durable docs or stable links",
    ),
    (
        "issue-url",
        re.compile(
            r"https?://(?:forgejo\.coilysiren\.me|github\.com)/[^/\s]+/[^/\s]+/issues/\d+\b",
            re.IGNORECASE,
        ),
        "replace issue URLs with durable docs or stable links",
    ),
    (
        "closing-keyword",
        re.compile(r"\b(?:closes|fixes|refs)\s+#\d+\b", re.IGNORECASE),
        "move the issue closure intent into a commit message or durable doc",
    ),
]


def main(argv: list[str] | None = None) -> int:
    if not has_hook_config(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0

    args = list(sys.argv[1:] if argv is None else argv)
    excludes = load_excludes(HOOK_ID)
    allow_globs = load_str_list(HOOK_ID, "allow_globs")
    violations: list[str] = []
    for rel in target_files(args):
        if rel in SKIP_FILES:
            continue
        if is_excluded(rel, allow_globs):
            continue
        if is_excluded(rel, excludes):
            continue
        text = read_text(rel)
        if text is None:
            continue
        violations.extend(scan_text(rel, text, RULES))

    if not violations:
        print(f"{HOOK_ID} check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(
        f"\n{len(violations)} issue-reference violation(s). "
        f"Move the reference into durable docs or a commit message.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

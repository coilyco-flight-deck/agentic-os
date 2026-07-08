#!/usr/bin/env python3
"""Reject unresolved placeholder prose in tracked text files.

This hook is intentionally staged rather than fleet-on by default. It catches
unfinished-agent artifacts like TODO implement, stub, placeholder, lorem, and
common apology/provenance phrases when a repo opts in with
``[tool.agentic-os.unresolved-placeholder-guard]``.
"""
from __future__ import annotations

import re
import sys

from agentic_os.config import has_hook_config, is_enabled, is_excluded, load_excludes, load_str_list
from agentic_os.pre_commit.text_scan import read_text, scan_text, target_files

HOOK_ID = "unresolved-placeholder-guard"
SKIP_FILES = {"pyproject.toml", ".agentic-os.toml"}

RULES = [
    (
        "todo-implement",
        re.compile(r"\bTODO\s+implement\b", re.IGNORECASE),
        "replace the TODO with finished prose or code",
    ),
    (
        "not-implemented-yet",
        re.compile(r"\bnot implemented yet\b", re.IGNORECASE),
        "finish the implementation or document a real fallback",
    ),
    (
        "placeholder",
        re.compile(r"\bplaceholder\b", re.IGNORECASE),
        "replace the placeholder with durable content",
    ),
    (
        "stub",
        re.compile(r"\bstub\b", re.IGNORECASE),
        "replace the stub with real content or move it to a documented todo",
    ),
    (
        "lorem",
        re.compile(r"\blorem(?: ipsum)?\b", re.IGNORECASE),
        "replace lorem text with actual copy",
    ),
    (
        "ai-provenance",
        re.compile(r"\b(?:as an AI language model|i(?:'m| am) sorry|apologies for the confusion|i am unable to)\b", re.IGNORECASE),
        "rewrite the generated apology or provenance text into repo-owned prose",
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
        f"\n{len(violations)} unresolved-placeholder violation(s). "
        f"Add a repo-specific allowlist or replace the unfinished prose.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

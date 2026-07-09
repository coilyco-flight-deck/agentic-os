#!/usr/bin/env python3
"""Reject direct issue references in tracked prose files.

This hook ships staged, not fleet-on. Repos opt in explicitly when they are
ready to replace issue-thread anchors with durable documentation links.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from agentic_os.config import has_hook_config, is_enabled, is_excluded, load_excludes, load_str_list
from agentic_os.pre_commit.text_scan import read_text, scan_text, target_files

HOOK_ID = "issue-reference-guard"
SKIP_FILES = {"pyproject.toml", ".agentic-os.toml"}
SKIP_DIRS = {"tests"}
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?")

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
        "closing-keyword",
        re.compile(r"\b(?:closes|fixes|refs)\s+#\d+\b", re.IGNORECASE),
        "move the issue closure intent into a commit message or durable doc",
    ),
]


def _is_fixture(rel: str) -> bool:
    path = Path(rel)
    return bool(path.parts and path.parts[0] in SKIP_DIRS)


def _strip_code_and_quotes(text: str) -> str:
    out: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("\n" if line.endswith("\n") else "")
            continue
        if in_fence or BLOCKQUOTE_RE.match(line):
            out.append("\n" if line.endswith("\n") else "")
            continue
        out.append(INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line))
    return "".join(out)


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
        if _is_fixture(rel):
            continue
        if is_excluded(rel, allow_globs):
            continue
        if is_excluded(rel, excludes):
            continue
        text = read_text(rel)
        if text is None:
            continue
        text = _strip_code_and_quotes(text)
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

#!/usr/bin/env python3
"""Reject commit-message subjects that don't match Conventional Commits 1.0.0.

Subject must match:
    <type>(<scope>)?!?: <subject>

where `<type>` is one of feat, fix, docs, style, refactor, perf, test,
build, ci, chore, revert. Optional `<scope>` in parens. Optional `!`
marks a breaking change.

Auto-generated commits (Merge, Revert, fixup!, squash!) are exempt.

Designed to coexist with the closes-issue hook. A subject like
`feat: add foo` plus a `closes #N` in the body satisfies both.

Usage:
    check-conventional-commit <commit-msg-file>

Wired as a `commit-msg` pre-commit hook via .pre-commit-hooks.yaml.
Exits 0 on accept, 1 on reject (with a dictation-friendly error).
"""
from __future__ import annotations

import re
import sys

TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

SUBJECT_RE = re.compile(
    r"^(?:" + "|".join(TYPES) + r")(?:\([\w/\-\.]+\))?!?: \S.*$"
)

EXEMPT_PREFIXES = ("Merge ", "Revert ", "fixup!", "squash!", "🚀")

ERROR = (
    "commit message rejected: subject must match Conventional Commits 1.0.0.\n"
    "  Format: <type>(<scope>)?!?: <subject>\n"
    f"  Allowed types: {', '.join(TYPES)}\n"
    "  Examples:\n"
    "    feat: add catalog-trifecta validator\n"
    "    fix(rollout): strip legacy blocks idempotently\n"
    "    feat!: drop language: script entry shape (BREAKING CHANGE)\n"
    "  Optional !-flag marks a breaking change.\n"
    "  Auto-generated subjects (Merge/Revert/fixup!/squash!/🚀) are exempt.\n"
)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        sys.stderr.write("usage: check-conventional-commit <commit-msg-file>\n")
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        raw = fh.read()
    # Strip pre-commit / git comment lines.
    body = re.sub(r"(?m)^#.*\n?", "", raw).strip()
    if not body:
        return 0
    subject = body.split("\n", 1)[0]
    if subject.startswith(EXEMPT_PREFIXES):
        return 0
    if SUBJECT_RE.match(subject):
        return 0
    sys.stderr.write(ERROR)
    sys.stderr.write(f"\nGot subject: {subject!r}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

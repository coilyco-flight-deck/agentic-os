"""Shared helpers for text-scanning pre-commit hooks."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

REPO_ROOT = Path.cwd()


def _git(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def normalize_rel(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/")))


def staged_files() -> list[str]:
    return [
        normalize_rel(tok)
        for tok in _git(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]).split("\0")
        if tok
    ]


def tracked_files() -> list[str]:
    return [normalize_rel(tok) for tok in _git(["ls-files", "-z"]).split("\0") if tok]


def target_files(args: list[str]) -> list[str]:
    if args:
        return [normalize_rel(arg) for arg in args]
    staged = staged_files()
    return staged if staged else tracked_files()


def read_text(rel: str) -> str | None:
    try:
        return (REPO_ROOT / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def scan_text(
    rel: str, text: str, rules: list[tuple[str, re.Pattern[str], str]]
) -> list[str]:
    hits: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule_id, matcher, message in rules:
            if matcher.search(line):
                hits.append(f"{rel}:{line_no}: {rule_id} - {message}")
    return hits

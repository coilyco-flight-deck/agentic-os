#!/usr/bin/env python3
"""Enforce the root CODE-REVIEW.md contract.

The root review contract is a catalog surface, not a loose style note. It
must name the repo-local invariants it defends, the historical issues it
guards against, and when it must be refreshed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from agentic_os.config import is_enabled

REPO_ROOT = Path.cwd()
HOOK_ID = "code-review-contract"
CODE_REVIEW = Path("CODE-REVIEW.md")

REQUIRED_H2 = [
    "Localized invariants",
    "Historical issues",
    "Update triggers",
]

GENERIC_REVIEW_RE = re.compile(r"\b(?:1|one)[- ]letter variable names\b", re.I)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def markdown_h2s(body: str) -> set[str]:
    headings: set[str] = set()
    in_code = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = H2_RE.match(stripped)
        if match:
            headings.add(re.sub(r"\s+", " ", match.group(1).strip()))
    return headings


def check_code_review_contract(repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    path = root / CODE_REVIEW
    if not path.is_file():
        return ["CODE-REVIEW.md missing. Every repo needs a root review-contract doc."]

    body = path.read_text(encoding="utf-8", errors="replace")
    violations: list[str] = []

    if not body.lstrip().startswith("#"):
        violations.append("CODE-REVIEW.md must start with a Markdown heading.")

    headings = markdown_h2s(body)
    missing = [h for h in REQUIRED_H2 if h not in headings]
    if missing:
        violations.append(
            "CODE-REVIEW.md missing required H2 section(s): "
            + ", ".join(f"## {h}" for h in missing)
            + ". Keep the contract focused on local invariants, historical "
            + "issues, and refresh triggers."
        )

    if GENERIC_REVIEW_RE.search(body):
        violations.append(
            "CODE-REVIEW.md contains generic-purpose review advice. "
            "Keep the contract focused on repo-local invariants and historical "
            "issues instead."
        )

    return violations


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    violations = check_code_review_contract()
    if not violations:
        print("code-review-contract check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(f"\n{len(violations)} code review contract violation(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

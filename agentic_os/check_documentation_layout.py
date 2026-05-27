#!/usr/bin/env python3
"""Enforce repo documentation placement.

Markdown documentation may live only in:
    1. the repo root, with a small universal filename allow-list;
    2. docs/*.md, with no docs subdirectories;
    3. skill folders (.agents/skills, .claude/skills, or skills).

The rule keeps repo documentation structured, flat, and discoverable. One-off
root Markdown files and nested docs trees drift quickly and make agents guess
where current information lives.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path.cwd()
MAX_MARKDOWN_LINES = 80
MAX_MARKDOWN_CHARS = 4_000

# Verbatim upstream files; exempt from size cap, matched by basename.
SIZE_CAP_EXEMPT_BASENAMES = {
    "CODE_OF_CONDUCT.md",
}

ROOT_MARKDOWN_ALLOWLIST = {
    "AGENTS.md",
    "CLAUDE.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "LICENSE.md",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
}

SKIP_DIR_NAMES = {
    ".claude",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".terraform",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

SKILL_PATHS = (
    (".agents", "skills"),
    (".claude", "skills"),
    ("skills",),
)


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def is_under_skill_path(rel: Path) -> bool:
    parts = rel.parts
    for skill_parts in SKILL_PATHS:
        n = len(skill_parts)
        if len(parts) >= n and parts[:n] == skill_parts:
            return True
    return False


def markdown_files() -> list[Path]:
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*.md"):
        rel = path.relative_to(REPO_ROOT)
        if should_skip(rel):
            continue
        out.append(rel)
    return sorted(out)


def check_docs_flatness() -> list[str]:
    docs = REPO_ROOT / "docs"
    if not docs.is_dir():
        return []
    violations: list[str] = []
    for path in sorted(docs.rglob("*")):
        rel = path.relative_to(REPO_ROOT)
        if should_skip(rel):
            continue
        if path.is_dir() and path != docs:
            violations.append(
                f"{rel}: docs/ must stay flat. Use filename prefixes instead "
                f"of docs subdirectories."
            )
    return violations


def is_example_readme(rel: Path) -> bool:
    # Go/Rust examples/<name>/README.md is idiomatic; exempt from flat-docs rule.
    parts = rel.parts
    if not parts or parts[0] != "examples" or rel.name != "README.md":
        return False
    return len(parts) in (2, 3)


def check_markdown_locations() -> list[str]:
    violations: list[str] = []
    for rel in markdown_files():
        if len(rel.parts) == 1:
            if rel.name not in ROOT_MARKDOWN_ALLOWLIST:
                allowed = ", ".join(sorted(ROOT_MARKDOWN_ALLOWLIST))
                violations.append(
                    f"{rel}: top-level Markdown filename is not allowed. "
                    f"Allowed root Markdown files: {allowed}. Move one-off "
                    f"docs into docs/."
                )
            continue
        if rel.parts[0] == "docs" and len(rel.parts) == 2:
            continue
        if is_under_skill_path(rel):
            continue
        if is_example_readme(rel):
            continue
        violations.append(
            f"{rel}: Markdown files may live only at repo root, docs/*.md, "
            f"or inside a skill folder."
        )
    return violations


def check_markdown_sizes() -> list[str]:
    violations: list[str] = []
    for rel in markdown_files():
        if rel.name in SIZE_CAP_EXEMPT_BASENAMES:
            continue
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        n_lines = len(text.splitlines())
        n_chars = len(text)
        if n_lines > MAX_MARKDOWN_LINES:
            violations.append(
                f"{rel}: {n_lines} lines exceeds the {MAX_MARKDOWN_LINES}-line "
                f"cap. Split large docs into smaller docs/*.md files."
            )
        if n_chars > MAX_MARKDOWN_CHARS:
            violations.append(
                f"{rel}: {n_chars} chars exceeds the {MAX_MARKDOWN_CHARS}-char "
                f"cap. Split large docs into smaller docs/*.md files."
            )
    return violations


def main() -> int:
    violations = (
        check_docs_flatness()
        + check_markdown_locations()
        + check_markdown_sizes()
    )
    if not violations:
        print("documentation-layout check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(f"\n{len(violations)} documentation layout violation(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

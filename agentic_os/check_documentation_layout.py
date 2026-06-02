#!/usr/bin/env python3
"""Enforce repo documentation placement and size.

This module is the single source of truth for Markdown size caps across the
agentic-os ecosystem. Docs (AGENTS.md, SKILL.md.template, handbook.md, etc.)
should point here by reference rather than restating numbers, so the caps
can never drift between code and prose.

Markdown documentation may live only in:
    1. the repo root, with a small universal filename allow-list;
    2. docs/*.md, with no docs subdirectories;
    3. skill folders (.agents/skills, .claude/skills, or skills), which may
       carry any support subdirs (scripts/, assets/, references/, agents/,
       ...) - the only flatness rule is that no nested SKILL.md may hide below
       the top-level skill dir, since the loader only sees top-level dirs;
    4. anywhere under an `examples/` directory at any depth, any .md filename.

Every Markdown file shares one size cap: MAX_MARKDOWN_LINES /
MAX_MARKDOWN_CHARS. SKILL.md is not special. CLAUDE.md is expected to be a
one-line `@AGENTS.md` pointer.

AGENTS.md may opt into a larger cap, per-repo, via config keys
`agents_md_max_lines` / `agents_md_max_chars` under the documentation-layout
hook section. Repos that don't set them get the standard cap for AGENTS.md
too. The canonical agentic-os-kai AGENTS.md is loader-bound (read on every
session) and holds universal-fire doctrine that can't split into docs/*.md
without losing unconditional firing, so that repo opts in; nothing else does.
"""
from __future__ import annotations

import sys
from pathlib import Path

from agentic_os.config import (
    get_int_option,
    is_enabled,
    is_excluded,
    load_excludes,
)

REPO_ROOT = Path.cwd()
HOOK_ID = "documentation-layout"
MAX_MARKDOWN_LINES = 80
MAX_MARKDOWN_CHARS = 4_000

# Standard AGENTS.md cap by default. Repos opt into a larger one via config
# keys agents_md_max_lines / agents_md_max_chars.
AGENTS_DEFAULT_MAX_LINES = MAX_MARKDOWN_LINES
AGENTS_DEFAULT_MAX_CHARS = MAX_MARKDOWN_CHARS

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
    excludes = load_excludes(HOOK_ID)
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*.md"):
        rel = path.relative_to(REPO_ROOT)
        if should_skip(rel):
            continue
        if is_excluded(rel, excludes):
            continue
        out.append(rel)
    return sorted(out)


def check_docs_flatness() -> list[str]:
    docs = REPO_ROOT / "docs"
    if not docs.is_dir():
        return []
    excludes = load_excludes(HOOK_ID)
    violations: list[str] = []
    for path in sorted(docs.rglob("*")):
        rel = path.relative_to(REPO_ROOT)
        if should_skip(rel):
            continue
        if is_excluded(rel, excludes):
            continue
        if path.is_dir() and path != docs:
            violations.append(
                f"{rel}: docs/ must stay flat. Use filename prefixes instead "
                f"of docs subdirectories."
            )
    return violations


def is_under_examples(rel: Path) -> bool:
    # Go/Rust examples/<name>/... is idiomatic at any depth and may contain
    # .md files of any name, not just README.md.
    return "examples" in rel.parts


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
        if is_under_examples(rel):
            continue
        violations.append(
            f"{rel}: Markdown files may live only at repo root, docs/*.md, "
            f"or inside a skill folder."
        )
    return violations


def check_skill_flatness(repo_root: Path | None = None) -> list[str]:
    """Flag nested sub-skills, not support material.

    The skill loader only sees top-level skill dirs, so a SKILL.md nested
    below the top level is invisible and must move up. Support subdirs
    (scripts/, assets/, references/, agents/, ...) are fine - the rule
    targets hidden sub-skills, not material that sits beside SKILL.md.
    """
    root = repo_root or REPO_ROOT
    excludes = load_excludes(HOOK_ID, root)
    violations: list[str] = []
    for skill_parts in SKILL_PATHS:
        skill_root = root.joinpath(*skill_parts)
        if not skill_root.is_dir():
            continue
        for skill_dir in sorted(skill_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            if should_skip(skill_dir.relative_to(root)):
                continue
            for nested in sorted(skill_dir.rglob("SKILL.md")):
                if nested.parent == skill_dir:
                    continue  # the skill's own top-level SKILL.md
                rel = nested.relative_to(root)
                if should_skip(rel):
                    continue
                if is_excluded(rel, excludes):
                    continue
                violations.append(
                    f"{rel}: nested SKILL.md must not hide below the top-level "
                    f"skill dir - the loader only sees top-level dirs. Move "
                    f"this sub-skill up to sit beside the others."
                )
    return violations


def caps_for(rel: Path) -> tuple[int, int]:
    if rel.name == "AGENTS.md":
        max_lines = get_int_option(
            HOOK_ID, "agents_md_max_lines", AGENTS_DEFAULT_MAX_LINES
        )
        max_chars = get_int_option(
            HOOK_ID, "agents_md_max_chars", AGENTS_DEFAULT_MAX_CHARS
        )
        return max_lines, max_chars
    return MAX_MARKDOWN_LINES, MAX_MARKDOWN_CHARS


def check_markdown_sizes() -> list[str]:
    violations: list[str] = []
    for rel in markdown_files():
        if rel.name in SIZE_CAP_EXEMPT_BASENAMES:
            continue
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        n_lines = len(text.splitlines())
        n_chars = len(text)
        max_lines, max_chars = caps_for(rel)
        if n_lines > max_lines:
            violations.append(
                f"{rel}: {n_lines} lines exceeds the {max_lines}-line "
                f"cap. Split large docs into smaller docs/*.md files."
            )
        if n_chars > max_chars:
            violations.append(
                f"{rel}: {n_chars} chars exceeds the {max_chars}-char "
                f"cap. Split large docs into smaller docs/*.md files."
            )
    return violations


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    violations = (
        check_docs_flatness()
        + check_markdown_locations()
        + check_markdown_sizes()
        + check_skill_flatness()
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

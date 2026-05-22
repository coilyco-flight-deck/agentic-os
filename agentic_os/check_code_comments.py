#!/usr/bin/env python3
"""Keep code comments short, durable, and non-contiguous.

Inline code documentation is allowed, but it must stay local and durable:
one standalone comment line, at most 90 characters. Longer explanations belong
in docs/*.md and should be linked or referenced from code by a short pointer.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path.cwd()
MAX_COMMENT_LINE_CHARS = 90

SKIP_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

LINE_COMMENT_PREFIXES = {
    ".bash": ("#",),
    ".c": ("//",),
    ".cc": ("//",),
    ".cpp": ("//",),
    ".cs": ("//",),
    ".go": ("//",),
    ".h": ("//",),
    ".hpp": ("//",),
    ".java": ("//",),
    ".js": ("//",),
    ".jsx": ("//",),
    ".kt": ("//",),
    ".kts": ("//",),
    ".lua": ("--",),
    ".mjs": ("//",),
    ".py": ("#",),
    ".rb": ("#",),
    ".rs": ("//",),
    ".sh": ("#",),
    ".ts": ("//",),
    ".tsx": ("//",),
    ".zsh": ("#",),
}

BLOCK_COMMENT_EXTS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".mjs",
    ".rs",
    ".ts",
    ".tsx",
}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def source_files() -> list[Path]:
    exts = set(LINE_COMMENT_PREFIXES) | BLOCK_COMMENT_EXTS
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT)
        if should_skip(rel):
            continue
        if path.suffix in exts:
            out.append(rel)
    return sorted(out)


def is_shebang_or_encoding(line: str, line_no: int) -> bool:
    stripped = line.strip()
    if line_no == 1 and stripped.startswith("#!"):
        return True
    if line_no <= 2 and "coding" in stripped and stripped.startswith("#"):
        return True
    return False


def is_comment_line(line: str, suffix: str, line_no: int) -> bool:
    if is_shebang_or_encoding(line, line_no):
        return False
    stripped = line.lstrip()
    for prefix in LINE_COMMENT_PREFIXES.get(suffix, ()):
        if stripped.startswith(prefix):
            return True
    if suffix in BLOCK_COMMENT_EXTS:
        return (
            stripped.startswith("/*")
            or stripped.startswith("*")
            or stripped.startswith("*/")
        )
    return False


def check_file(rel: Path) -> list[str]:
    path = REPO_ROOT / rel
    violations: list[str] = []
    previous_comment_line: int | None = None
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        if not is_comment_line(line, path.suffix, line_no):
            previous_comment_line = None
            continue
        if len(line) > MAX_COMMENT_LINE_CHARS:
            violations.append(
                f"{rel}:{line_no}: comment line is {len(line)} chars, over "
                f"the {MAX_COMMENT_LINE_CHARS}-char cap. Move durable detail "
                f"to docs/."
            )
        if previous_comment_line is not None:
            violations.append(
                f"{rel}:{line_no}: contiguous comment line after line "
                f"{previous_comment_line}. Keep code comments to one line."
            )
        previous_comment_line = line_no
    return violations


def main() -> int:
    violations: list[str] = []
    for rel in source_files():
        violations.extend(check_file(rel))
    if not violations:
        print("code-comments check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(f"\n{len(violations)} code comment violation(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

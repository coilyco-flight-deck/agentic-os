#!/usr/bin/env python3
"""Keep code comments short, durable, and non-contiguous.

Inline code documentation is allowed, but it must stay local and durable:
up to two consecutive comment lines, each at most 90 characters. Longer
explanations belong in docs/*.md and should be linked or referenced from
code by a short pointer.

A contiguous comment block at the very top of the file - the header above
the first content line - is exempt from the two-line limit, so license and
teaching headers are fine. The cap only governs comments after content
begins. Shebang and encoding lines are part of the preamble, not content,
so a header block may follow them.

YAML is stricter: a key-sorter rearranges YAML lines, so a comment anywhere
but the very top would drift away from whatever it described. YAML therefore
allows comments only as that top header block - everything above the first
content line. Once a content line appears, any later comment is a violation.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from agentic_os.config import is_enabled, is_excluded, load_excludes

REPO_ROOT = Path.cwd()
HOOK_ID = "code-comments"
MAX_COMMENT_LINE_CHARS = 90
MAX_CONTIGUOUS_COMMENT_LINES = 2

YAML_EXTS = {".yaml", ".yml"}

# Header of a `|`/`>` block scalar (`run: |`, `- |`). Lines indented under it
# are string content, so a leading `#` there is bash, not a YAML comment.
_BLOCK_SCALAR_HEADER = re.compile(
    r"(?::|^\s*-)\s*[|>][0-9+-]*\s*(?:#.*)?$"
)


def starts_block_scalar(line: str) -> bool:
    return bool(_BLOCK_SCALAR_HEADER.search(line))

SKIP_DIR_NAMES = {
    ".claude",
    ".git",
    ".terraform",
    "build",
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
    ".yaml": ("#",),
    ".yml": ("#",),
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
    excludes = load_excludes(HOOK_ID)
    out: list[Path] = []
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True,
            check=True,
            text=True,
            cwd=REPO_ROOT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not a git repo or git unavailable, fall back to rglob walk.
        for path in REPO_ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO_ROOT)
            if should_skip(rel) or is_excluded(rel, excludes):
                continue
            if path.suffix in exts:
                out.append(rel)
        return sorted(out)
    for entry in result.stdout.split("\x00"):
        if not entry:
            continue
        rel = Path(entry)
        if should_skip(rel) or is_excluded(rel, excludes):
            continue
        if rel.suffix in exts and (REPO_ROOT / rel).is_file():
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


def char_cap_violation(rel: Path, line_no: int, line: str) -> str:
    return (
        f"{rel}:{line_no}: comment line is {len(line)} chars, over "
        f"the {MAX_COMMENT_LINE_CHARS}-char cap. Move durable detail "
        f"to docs/."
    )


def scan_yaml(rel: Path, suffix: str, lines: list[str]) -> list[str]:
    violations: list[str] = []
    block_indent: int | None = None
    seen_content = False
    for line_no, line in enumerate(lines, start=1):
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            # Blank or deeper-indented lines are block-scalar content, so a
            # leading `#` is not a YAML comment. A dedent ends the block.
            if line.strip() == "" or indent > block_indent:
                continue
            block_indent = None
        if is_comment_line(line, suffix, line_no):
            if len(line) > MAX_COMMENT_LINE_CHARS:
                violations.append(char_cap_violation(rel, line_no, line))
            if seen_content:
                violations.append(
                    f"{rel}:{line_no}: YAML comment below the top header "
                    f"block. A key-sorter would drift it away from its "
                    f"target. Keep YAML comments above the first content "
                    f"line; move the rest to docs/."
                )
            continue
        if line.strip() != "":
            seen_content = True
        if starts_block_scalar(line):
            block_indent = indent
    return violations


def scan_lines(rel: Path, suffix: str, lines: list[str]) -> list[str]:
    if suffix in YAML_EXTS:
        return scan_yaml(rel, suffix, lines)
    violations: list[str] = []
    streak_start: int | None = None
    streak_len = 0
    seen_content = False
    for line_no, line in enumerate(lines, start=1):
        if not is_comment_line(line, suffix, line_no):
            if line.strip() != "" and not is_shebang_or_encoding(line, line_no):
                seen_content = True
            streak_start = None
            streak_len = 0
            continue
        if len(line) > MAX_COMMENT_LINE_CHARS:
            violations.append(char_cap_violation(rel, line_no, line))
        # The top-of-file header block (comments above any content) is exempt
        # from the contiguous-block limit. See docstring.
        if not seen_content:
            continue
        if streak_start is None:
            streak_start = line_no
            streak_len = 1
        else:
            streak_len += 1
            if streak_len > MAX_CONTIGUOUS_COMMENT_LINES:
                violations.append(
                    f"{rel}:{line_no}: comment block of {streak_len} lines "
                    f"starting at {streak_start}. Keep contiguous comment "
                    f"blocks to {MAX_CONTIGUOUS_COMMENT_LINES} lines. Move "
                    f"longer explanations to docs/."
                )
    return violations


def check_file(rel: Path) -> list[str]:
    path = REPO_ROOT / rel
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return scan_lines(rel, path.suffix, lines)


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
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

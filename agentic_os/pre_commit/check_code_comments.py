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

Two per-repo dials under ``[tool.agentic-os.code-comments]`` change the two
paragraphs above, both defaulting off so no repo moves until it opts in:

``header_cap = true``
    Applies the two-line cap to the top-of-file header too, for YAML and KDL.
    The exemption let a header grow without bound, which is where explanation
    accumulates once every other position is capped.

``yaml_comments_below_content = true``
    Drops the YAML-only top-block restriction, so YAML takes the same capped
    comments every other language does. The restriction exists solely because
    ``yaml-strict`` sorts keys and would drift a comment off its target. A repo
    that does not run that hook has no sorter, so the restriction only pushes
    per-key rationale into one unbounded block at the top. Setting this while
    ``yaml-strict`` is configured is refused rather than silently obeyed: that
    combination sorts the keys and then strips the comments.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from agentic_os.config import (
    get_bool_option,
    is_enabled,
    is_excluded,
    load_excludes,
)
from agentic_os.pre_commit.tree import is_repo_content

REPO_ROOT = Path.cwd()
HOOK_ID = "code-comments"
MAX_COMMENT_LINE_CHARS = 90
MAX_CONTIGUOUS_COMMENT_LINES = 2

YAML_EXTS = {".yaml", ".yml"}

# Where a top-of-file header is data-like rather than prose: a spec, a manifest,
# a values file. Prose languages keep the exemption.
HEADER_CAPPED_EXTS = {".kdl", ".yaml", ".yml"}

PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"
YAML_SORTER_HOOK = "yaml-strict"

# Header of a `|`/`>` block scalar (`run: |`, `- |`). Lines indented under it
# are string content, so a leading `#` there is bash, not a YAML comment.
_BLOCK_SCALAR_HEADER = re.compile(
    r"(?::|^\s*-)\s*[|>][0-9+-]*\s*(?:#.*)?$"
)


def starts_block_scalar(line: str) -> bool:
    return bool(_BLOCK_SCALAR_HEADER.search(line))

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
    ".kdl": ("//",),
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
    ".kdl",
    ".kt",
    ".kts",
    ".mjs",
    ".rs",
    ".ts",
    ".tsx",
}


def should_skip(path: Path) -> bool:
    return not is_repo_content(path, REPO_ROOT)


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


def block_state_after(line: str, suffix: str, in_block: bool) -> bool:
    """Return whether a `/* ... */` block is still open after this line.

    A leading `*` is also the dereference operator, so continuation lines are
    only recognizable from real open/close state rather than per-line shape.
    """
    prefixes = LINE_COMMENT_PREFIXES.get(suffix, ())
    index = 0
    end = len(line)
    while index < end:
        if in_block:
            if line.startswith("*/", index):
                in_block = False
                index += 2
                continue
            index += 1
            continue
        if line.startswith("/*", index):
            in_block = True
            index += 2
            continue
        if any(line.startswith(prefix, index) for prefix in prefixes):
            # Rest of the line is a line comment, so no block can open in it.
            return False
        if line[index] == '"':
            index = skip_string(line, index)
            continue
        index += 1
    return in_block


def skip_string(line: str, index: int) -> int:
    """Return the index just past the double-quoted run starting at `index`."""
    index += 1
    end = len(line)
    while index < end:
        if line[index] == "\\":
            index += 2
            continue
        if line[index] == '"':
            return index + 1
        index += 1
    return index


def is_comment_line(
    line: str,
    suffix: str,
    line_no: int,
    in_block: bool = False,
) -> bool:
    if is_shebang_or_encoding(line, line_no):
        return False
    if in_block:
        return True
    stripped = line.lstrip()
    for prefix in LINE_COMMENT_PREFIXES.get(suffix, ()):
        if stripped.startswith(prefix):
            return True
    if suffix in BLOCK_COMMENT_EXTS:
        return stripped.startswith("/*")
    return False


def char_cap_violation(rel: Path, line_no: int, line: str) -> str:
    return (
        f"{rel.as_posix()}:{line_no}: comment line is {len(line)} chars, over "
        f"the {MAX_COMMENT_LINE_CHARS}-char cap. Move durable detail "
        f"to docs/."
    )


def header_cap_violation(rel: Path, line_no: int, count: int) -> str:
    return (
        f"{rel.as_posix()}:{line_no}: top-of-file comment header is {count} lines, "
        f"over the {MAX_CONTIGUOUS_COMMENT_LINES}-line cap. Move durable "
        f"detail to docs/ and leave a short pointer."
    )


def scan_yaml(
    rel: Path,
    suffix: str,
    lines: list[str],
    *,
    header_cap: bool = False,
    comments_below_content: bool = False,
) -> list[str]:
    violations: list[str] = []
    block_indent: int | None = None
    seen_content = False
    header_lines = 0
    streak_start: int | None = None
    streak_len = 0
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
            if not seen_content:
                # Counted across blank lines: a blank line inside the header
                # would otherwise reset the streak and uncap the whole block.
                header_lines += 1
                if header_cap and header_lines == MAX_CONTIGUOUS_COMMENT_LINES + 1:
                    violations.append(
                        header_cap_violation(rel, line_no, header_lines)
                    )
            elif not comments_below_content:
                violations.append(
                    f"{rel.as_posix()}:{line_no}: YAML comment below the top header "
                    f"block. A key-sorter would drift it away from its "
                    f"target. Keep YAML comments above the first content "
                    f"line; move the rest to docs/."
                )
            else:
                if streak_start is None:
                    streak_start, streak_len = line_no, 1
                else:
                    streak_len += 1
                    if streak_len > MAX_CONTIGUOUS_COMMENT_LINES:
                        violations.append(
                            streak_violation(rel, line_no, streak_start, streak_len)
                        )
            continue
        streak_start, streak_len = None, 0
        if line.strip() != "":
            seen_content = True
        if starts_block_scalar(line):
            block_indent = indent
    return violations


def streak_violation(
    rel: Path, line_no: int, streak_start: int, streak_len: int
) -> str:
    return (
        f"{rel.as_posix()}:{line_no}: comment block of {streak_len} lines "
        f"starting at {streak_start}. Keep contiguous comment "
        f"blocks to {MAX_CONTIGUOUS_COMMENT_LINES} lines. Move "
        f"longer explanations to docs/."
    )


def scan_lines(
    rel: Path,
    suffix: str,
    lines: list[str],
    *,
    header_cap: bool = False,
    comments_below_content: bool = False,
) -> list[str]:
    if suffix in YAML_EXTS:
        return scan_yaml(
            rel,
            suffix,
            lines,
            header_cap=header_cap,
            comments_below_content=comments_below_content,
        )
    violations: list[str] = []
    header_lines = 0
    streak_start: int | None = None
    streak_len = 0
    seen_content = False
    tracks_blocks = suffix in BLOCK_COMMENT_EXTS
    in_block = False
    for line_no, line in enumerate(lines, start=1):
        opened_in_block = in_block
        if tracks_blocks:
            in_block = block_state_after(line, suffix, opened_in_block)
        if not is_comment_line(line, suffix, line_no, opened_in_block):
            if line.strip() != "" and not is_shebang_or_encoding(line, line_no):
                seen_content = True
            streak_start = None
            streak_len = 0
            continue
        if len(line) > MAX_COMMENT_LINE_CHARS:
            violations.append(char_cap_violation(rel, line_no, line))
        # The top-of-file header block (comments above any content) is exempt
        # from the contiguous-block limit unless the repo opts in. See docstring.
        if not seen_content:
            header_lines += 1
            if (
                header_cap
                and suffix in HEADER_CAPPED_EXTS
                and header_lines == MAX_CONTIGUOUS_COMMENT_LINES + 1
            ):
                violations.append(header_cap_violation(rel, line_no, header_lines))
            continue
        if streak_start is None:
            streak_start = line_no
            streak_len = 1
        else:
            streak_len += 1
            if streak_len > MAX_CONTIGUOUS_COMMENT_LINES:
                violations.append(
                    streak_violation(rel, line_no, streak_start, streak_len)
                )
    return violations


def check_file(
    rel: Path,
    *,
    header_cap: bool = False,
    comments_below_content: bool = False,
) -> list[str]:
    path = REPO_ROOT / rel
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return scan_lines(
        rel,
        path.suffix,
        lines,
        header_cap=header_cap,
        comments_below_content=comments_below_content,
    )


def sorts_yaml_keys(repo_root: Path | None = None) -> bool:
    """Whether this repo configures the YAML key-sorter this hook defers to.

    Read textually rather than through a YAML parser: this hook ships with no
    dependencies, and a hook id is a literal string in the config either way.
    """
    config = (repo_root or REPO_ROOT) / PRE_COMMIT_CONFIG
    try:
        text = config.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return f"id: {YAML_SORTER_HOOK}" in text


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    header_cap = get_bool_option(HOOK_ID, "header_cap", False)
    comments_below_content = get_bool_option(
        HOOK_ID, "yaml_comments_below_content", False
    )
    if comments_below_content and sorts_yaml_keys():
        sys.stderr.write(
            f"FAIL: yaml_comments_below_content is set while {YAML_SORTER_HOOK} "
            f"is configured in {PRE_COMMIT_CONFIG}. That sorter reorders keys "
            f"and strips comments, so a comment placed beside its key would "
            f"be moved and then deleted. Drop one of the two.\n"
        )
        return 1
    violations: list[str] = []
    for rel in source_files():
        violations.extend(
            check_file(
                rel,
                header_cap=header_cap,
                comments_below_content=comments_below_content,
            )
        )
    if not violations:
        print("code-comments check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(f"\n{len(violations)} code comment violation(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

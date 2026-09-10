#!/usr/bin/env python3
"""Keep code comments short, durable, and non-contiguous.

Standalone comment lines take a char cap and a contiguous-block cap, and a module
docstring takes its own line cap, because explanation belongs on a docs page
where it is read rather than in a file where it is not. Python is classified by
tokenize, so a hash inside a string is not a comment. YAML is stricter: a
key-sorter drifts any comment below the header away from its target.
Caps: docs/catalog-caps-reference.md.
"""

from __future__ import annotations

import ast
import io
import re
import subprocess
import sys
import tokenize
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
MAX_DOCSTRING_LINES = 8

YAML_EXTS = {".yaml", ".yml"}

# Where a top-of-file header is data-like rather than prose: a spec, a manifest,
# a values file. Prose languages keep the exemption.
HEADER_CAPPED_EXTS = {".kdl", ".yaml", ".yml"}

PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"
YAML_SORTER_HOOK = "yaml-strict"

# Header of a `|`/`>` block scalar (`run: |`, `- |`). Lines indented under it
# are string content, so a leading `#` there is bash, not a YAML comment.
_BLOCK_SCALAR_HEADER = re.compile(r"(?::|^\s*-)\s*[|>][0-9+-]*\s*(?:#.*)?$")


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

# Languages whose backtick strings span lines and hold arbitrary text. A glob
# like `audit/*.jsonl` inside one would otherwise open a phantom block comment.
RAW_STRING_EXTS = {".go", ".js", ".jsx", ".mjs", ".ts", ".tsx"}

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


def block_state_after(
    line: str, suffix: str, in_block: bool, in_raw: bool = False
) -> tuple[bool, bool]:
    """Return `/* ... */` and raw-string openness after this line.

    A leading `*` is also the dereference operator, so continuation lines are
    only recognizable from real open/close state rather than per-line shape.
    Raw strings are tracked for the same reason in reverse: they run across
    lines and hold arbitrary text, so a `/*` inside one opens nothing.
    """
    prefixes = LINE_COMMENT_PREFIXES.get(suffix, ())
    raw_delim = "`" if suffix in RAW_STRING_EXTS else None
    index = 0
    end = len(line)
    while index < end:
        if in_raw:
            if raw_delim and line.startswith(raw_delim, index):
                in_raw = False
            index += 1
            continue
        if in_block:
            if line.startswith("*/", index):
                in_block = False
                index += 2
                continue
            index += 1
            continue
        if raw_delim and line.startswith(raw_delim, index):
            in_raw = True
            index += 1
            continue
        if line.startswith("/*", index):
            in_block = True
            index += 2
            continue
        if any(line.startswith(prefix, index) for prefix in prefixes):
            # Rest of the line is a line comment, so no block can open in it.
            return False, in_raw
        if line[index] == '"':
            index = skip_string(line, index)
            continue
        index += 1
    return in_block, in_raw


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


def docstring_violations(rel: Path, lines: list[str]) -> list[str]:
    """Refuse a module docstring that is longer than a pointer.

    A module docstring is where an agent puts an essay when the page it belongs
    on does not exist yet, and nothing capped it until aosx grew a 458-line one.
    Eight lines holds what the file is and where the rest lives. Per-line chars
    take the comment-line cap, since both are the same kind of writing.
    """
    try:
        tree = ast.parse("\n".join(lines))
    except (SyntaxError, ValueError):
        return []
    text = ast.get_docstring(tree)
    if not text:
        return []
    found: list[str] = []
    body = text.splitlines()
    if len(body) > MAX_DOCSTRING_LINES:
        found.append(
            f"{rel.as_posix()}:1: the module docstring is {len(body)} lines, "
            f"over the {MAX_DOCSTRING_LINES}-line cap. Move the durable half to "
            f"docs/ or guides/ and leave a pointer."
        )
    for offset, line in enumerate(body, start=1):
        if len(line) > MAX_COMMENT_LINE_CHARS:
            found.append(
                f"{rel.as_posix()}:{offset}: docstring line is {len(line)} "
                f"chars, over the {MAX_COMMENT_LINE_CHARS}-char cap."
            )
    return found


def python_comment_lines(lines: list[str]) -> set[int] | None:
    """Line numbers holding a real COMMENT token, or None if the source will not parse.

    A `#` inside a string is not a comment and a line-prefix scan cannot tell the
    difference, so Python is classified by its own tokenizer rather than by shape.
    Returns None rather than a guess when tokenizing fails, so the caller falls
    back to the prefix scan on a file it could not read.
    """
    try:
        stream = io.StringIO("\n".join(lines)).readline
        return {
            token.start[0]
            for token in tokenize.generate_tokens(stream)
            if token.type == tokenize.COMMENT
        }
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return None


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


# A generator owns every byte in here, so the comments cannot move and an edit
# does not survive the next rollout. Contract in the module docstring.
MANAGED_BEGIN_RE = re.compile(r"^\s*#\s*BEGIN managed by ")
MANAGED_END_RE = re.compile(r"^\s*#\s*END managed by ")


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
    managed_from: int | None = None
    for line_no, line in enumerate(lines, start=1):
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            # Blank or deeper-indented lines are block-scalar content, so a
            # leading `#` is not a YAML comment. A dedent ends the block.
            if line.strip() == "" or indent > block_indent:
                continue
            block_indent = None
        if is_comment_line(line, suffix, line_no):
            if MANAGED_END_RE.match(line):
                managed_from = None
                streak_start, streak_len = None, 0
                continue
            if MANAGED_BEGIN_RE.match(line):
                managed_from = line_no
                streak_start, streak_len = None, 0
                continue
            if managed_from is not None:
                continue
            if len(line) > MAX_COMMENT_LINE_CHARS:
                violations.append(char_cap_violation(rel, line_no, line))
            if not seen_content:
                # Counted across blank lines: a blank line inside the header
                # would otherwise reset the streak and uncap the whole block.
                header_lines += 1
                if header_cap and header_lines == MAX_CONTIGUOUS_COMMENT_LINES + 1:
                    violations.append(header_cap_violation(rel, line_no, header_lines))
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
    if managed_from is not None:
        violations.append(unterminated_region_violation(rel, managed_from))
    return violations


def unterminated_region_violation(rel: Path, start: int) -> str:
    return (
        f"{rel.as_posix()}:{start}: managed region opened here and never closed. "
        f"Everything after it is exempt, so an unterminated marker is a silent "
        f"whole-file opt-out. Close it with a matching `# END managed by ...`."
    )


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
    tokenized = python_comment_lines(lines) if suffix == ".py" else None
    if suffix == ".py":
        violations.extend(docstring_violations(rel, lines))
    in_block = False
    in_raw = False
    for line_no, line in enumerate(lines, start=1):
        opened_in_block = in_block
        opened_in_raw = in_raw
        if tracks_blocks:
            in_block, in_raw = block_state_after(
                line, suffix, opened_in_block, opened_in_raw
            )
        if tokenized is not None:
            # A trailing comment shares its line with code, and every cap here
            # is written for a standalone one. Both signals have to agree.
            commented = (
                line_no in tokenized
                and line.lstrip().startswith("#")
                and not is_shebang_or_encoding(line, line_no)
            )
        else:
            commented = not opened_in_raw and is_comment_line(
                line, suffix, line_no, opened_in_block
            )
        if not commented:
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
    # On by default since #1119. The docstring above carries the reason.
    header_cap = get_bool_option(HOOK_ID, "header_cap", True)
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

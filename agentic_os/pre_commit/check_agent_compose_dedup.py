#!/usr/bin/env python3
"""Reject content duplicated across AGENTS.COMPOSE.md sources or with AGENTS.md.

agent-compose pulls AGENTS.COMPOSE.md doctrine into global
composed context, shared across harnesses by default. Two failure modes waste a
session's context budget:

    1. The same doctrine stated in two AGENTS.COMPOSE.md sources, so it composes
       twice.
    2. Doctrine in an AGENTS.COMPOSE.md that is also in the repo's own AGENTS.md,
       which a harness already loads through its normal cascade - so it loads
       once from the cascade and again from the composed file.

This hook flags significant lines (long enough to be real doctrine, not markdown
scaffolding) that appear in more than one source, or in a source and AGENTS.md.

Tunables under [tool.agentic-os.agent-compose-dedup]:
    min_line_chars - shortest line considered significant (default 24)
Opt out with `enabled = false` under the same section.
"""

from __future__ import annotations

import sys
from pathlib import Path

from agentic_os.frontmatter import split_frontmatter
from agentic_os.config import get_int_option, is_enabled, is_excluded, load_excludes
from agentic_os.pre_commit.tree import is_repo_content

REPO_ROOT = Path.cwd()
HOOK_ID = "agent-compose-dedup"
SOURCE_FILENAME = "AGENTS.COMPOSE.md"
DEFAULT_MIN_LINE_CHARS = 24


def _significant_lines(text: str, min_chars: int) -> set[str]:
    """Non-trivial doctrine lines: prose, not headings/bullets/fences/frontmatter."""
    out: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < min_chars:
            continue
        if line.startswith(("#", ">", "```", "- ", "* ", "|")) or line == "---":
            continue
        out.add(line)
    return out


def source_files(root: Path) -> list[Path]:
    excludes = load_excludes(HOOK_ID, root)
    out: list[Path] = []
    for path in root.rglob(SOURCE_FILENAME):
        rel = path.relative_to(root)
        # A composed bundle carries copies of the sources measured here, so a
        # bake would charge the budget twice. Output is not a source.
        if not is_repo_content(rel, root) or is_excluded(rel, excludes):
            continue
        out.append(rel)
    return sorted(out)


def find_violations(root: Path) -> list[str]:
    min_chars = get_int_option(HOOK_ID, "min_line_chars", DEFAULT_MIN_LINE_CHARS, root)
    sources = source_files(root)

    # Map each significant source line to the files it appears in (frontmatter
    # stripped, since source-selection directives are not composed content).
    line_to_files: dict[str, set[str]] = {}
    for rel in sources:
        _metadata, body = split_frontmatter(
            (root / rel).read_text(encoding="utf-8", errors="replace")
        )
        for line in _significant_lines(body, min_chars):
            line_to_files.setdefault(line, set()).add(str(rel))

    agents = root / "AGENTS.md"
    agents_lines = (
        _significant_lines(
            agents.read_text(encoding="utf-8", errors="replace"), min_chars
        )
        if agents.is_file()
        else set()
    )

    violations: list[str] = []
    for line, files in sorted(line_to_files.items()):
        excerpt = line if len(line) <= 60 else line[:57] + "..."
        if len(files) > 1:
            violations.append(
                f"duplicated across {', '.join(sorted(files))}: {excerpt!r}"
            )
        elif line in agents_lines:
            violations.append(
                f"{next(iter(files))} duplicates AGENTS.md (already cascade-loaded): "
                f"{excerpt!r}"
            )
    return violations


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    violations = find_violations(REPO_ROOT)
    if not violations:
        print("agent-compose-dedup check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(f"\n{len(violations)} agent-compose dedup violation(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

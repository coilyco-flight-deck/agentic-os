#!/usr/bin/env python3
"""Assert a repo does not host skills owned by another repo.

A `coding-<repo>` or `repo-<name>` skill belongs inside the repo it describes,
not in a shared operating-context repo. Opt-in: it ships in the suite and no-ops
unless the repo declares [tool.agentic-os.misplaced-skills] with `deny` globs and
optional `allow` exceptions. Symlinked folders are skipped, since a symlink is
sourced elsewhere. Schema and rollout: docs/skill-discipline-authoring.md.
"""
from __future__ import annotations

import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, NoReturn

from agentic_os.config import is_enabled, load_str_list

HOOK_ID = "misplaced-skills"
TRACKER = "docs/skill-discipline-authoring.md"

SKILLS_DIR_CANDIDATES = (".agents/skills", ".claude/skills", "skills")


def fail(names: list[str], deny: list[str]) -> NoReturn:
    print(
        f"check-{HOOK_ID}: repo-specific skills must live in their own repo, "
        "not here:",
        file=sys.stderr,
    )
    for name in names:
        print(f"  - {name}", file=sys.stderr)
    print(
        f"  matched a deny glob {deny} in [tool.agentic-os.{HOOK_ID}]",
        file=sys.stderr,
    )
    print(
        "  move each skill into the repo it describes, or add it to `allow` if "
        "it genuinely belongs here",
        file=sys.stderr,
    )
    print(f"  see {TRACKER}", file=sys.stderr)
    sys.exit(1)


def find_skills_dir(root: Path) -> Path | None:
    for candidate in SKILLS_DIR_CANDIDATES:
        d = root / candidate
        if d.is_dir():
            return d
    return None


def misplaced(names: Iterable[str], deny: list[str], allow: list[str]) -> list[str]:
    """Return sorted skill names matching a deny glob and no allow glob."""
    out = [
        name
        for name in names
        if any(fnmatch(name, p) for p in deny)
        and not any(fnmatch(name, p) for p in allow)
    ]
    return sorted(out)


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0

    deny = load_str_list(HOOK_ID, "deny")
    if not deny:
        return 0  # opt-in: no deny list means nothing to enforce

    allow = load_str_list(HOOK_ID, "allow")
    skills_dir = find_skills_dir(Path.cwd())
    if skills_dir is None:
        return 0

    names = [
        d.name
        for d in sorted(skills_dir.iterdir())
        if d.is_dir() and not d.is_symlink() and (d / "SKILL.md").is_file()
    ]
    bad = misplaced(names, deny, allow)
    if bad:
        fail(bad, deny)
    return 0


if __name__ == "__main__":
    sys.exit(main())

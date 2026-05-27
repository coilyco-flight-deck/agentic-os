#!/usr/bin/env python3
"""pre-commit hook: assert every repo in data/repo-registry.md has a kind: repo pointer skill.

Walks `data/repo-registry.md` for the canonical repo list and asserts that
`.agents/skills/<repo-name>/SKILL.md` exists for each entry, plus a matching
`kind: repo` row in `.agents/skills/categories.yaml`. Pointer-shape rules
(description prefix, body bullets, line cap) are enforced by validate-skills;
this hook covers the presence check that validate-skills cannot do alone.

No-ops when either `data/repo-registry.md` or `.agents/skills/categories.yaml`
is missing, so the hook can ride in every consumer's managed block and only
fire in agentic-os-kai.

Schema and rollout: coilysiren/agentic-os-kai#312, #317.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NoReturn

from agentic_os.config import is_enabled

HOOK_ID = "repo-pointer-skills"
TRACKER = "coilysiren/agentic-os-kai#312"

REPO_ROOT = Path.cwd()
REGISTRY_PATH = REPO_ROOT / "data" / "repo-registry.md"
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
CATEGORIES_PATH = SKILLS_DIR / "categories.yaml"

# Match the canonical `[`coilysiren/<name>`]` bullet shape in repo-registry.md.
REGISTRY_LINE_RE = re.compile(r"\[`coilysiren/(?P<name>[A-Za-z0-9._-]+)`\]")

try:
    import yaml  # type: ignore[import-untyped, unused-ignore]
except ImportError:  # pragma: no cover
    print(
        f"check-{HOOK_ID}: PyYAML required. The hook entry in .pre-commit-hooks.yaml "
        f"declares additional_dependencies: [pyyaml].",
        file=sys.stderr,
    )
    sys.exit(1)


def fail(msgs: list[str]) -> NoReturn:
    for m in msgs:
        print(f"check-{HOOK_ID}: {m}", file=sys.stderr)
    print(f"  see {TRACKER} for schema", file=sys.stderr)
    sys.exit(1)


def parse_registry(text: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        m = REGISTRY_LINE_RE.search(line)
        if not m:
            continue
        name = m.group("name")
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def load_repo_categories() -> dict[str, dict]:
    with CATEGORIES_PATH.open() as fh:
        data = yaml.safe_load(fh) or {}
    out: dict[str, dict] = {}
    for cat in data.get("categories") or []:
        if cat.get("kind") == "repo":
            repo = cat.get("repo")
            if isinstance(repo, str):
                out[repo] = cat
    return out


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0

    if not REGISTRY_PATH.is_file():
        return 0
    if not CATEGORIES_PATH.is_file():
        return 0

    names = parse_registry(REGISTRY_PATH.read_text())
    if not names:
        return 0

    cats = load_repo_categories()

    failures: list[str] = []
    for name in names:
        skill_md = SKILLS_DIR / name / "SKILL.md"
        if not skill_md.is_file():
            failures.append(
                f"repo {name!r} listed in data/repo-registry.md has no pointer "
                f"skill at .agents/skills/{name}/SKILL.md"
            )
        if name not in cats:
            failures.append(
                f"repo {name!r} listed in data/repo-registry.md has no "
                f"`kind: repo` entry in .agents/skills/categories.yaml"
            )

    if failures:
        fail(failures)
    return 0


if __name__ == "__main__":
    sys.exit(main())

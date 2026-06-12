#!/usr/bin/env python3
"""Cap the size of AGENTS.COMPOSE.md sources, per file and per repo.

AGENTS.COMPOSE.md sources are composed into always-loaded global context
(agent-compose, forgejo #134), shared across harnesses by default and sliced
when frontmatter requires it. Their size matters in a way ordinary docs do not.
The general documentation-layout hook already caps each Markdown file. The
value this hook adds is the per-repo AGGREGATE budget: the sum of all
AGENTS.COMPOSE.md a repo contributes to composed context, which no per-file cap
bounds.

Caps (override per-repo under [tool.agentic-os.agent-compose-size]):
    max_source_chars  - per AGENTS.COMPOSE.md file (default 4000)
    max_total_chars   - sum across the repo's AGENTS.COMPOSE.md (default 12000)

Opt out with `enabled = false` under the same section. Frontmatter is counted:
it is small and bounding the raw file keeps the check simple and conservative.
"""
from __future__ import annotations

import sys
from pathlib import Path

from agentic_os.pre_commit.check_documentation_layout import should_skip
from agentic_os.config import get_int_option, is_enabled, is_excluded, load_excludes

REPO_ROOT = Path.cwd()
HOOK_ID = "agent-compose-size"
SOURCE_FILENAME = "AGENTS.COMPOSE.md"
DEFAULT_MAX_SOURCE_CHARS = 4_000
DEFAULT_MAX_TOTAL_CHARS = 12_000


def source_files(root: Path) -> list[Path]:
    excludes = load_excludes(HOOK_ID, root)
    out: list[Path] = []
    for path in root.rglob(SOURCE_FILENAME):
        rel = path.relative_to(root)
        if should_skip(rel) or is_excluded(rel, excludes):
            continue
        out.append(rel)
    return sorted(out)


def find_violations(root: Path) -> list[str]:
    max_source = get_int_option(HOOK_ID, "max_source_chars", DEFAULT_MAX_SOURCE_CHARS, root)
    max_total = get_int_option(HOOK_ID, "max_total_chars", DEFAULT_MAX_TOTAL_CHARS, root)
    violations: list[str] = []
    total = 0
    for rel in source_files(root):
        n_chars = len((root / rel).read_text(encoding="utf-8", errors="replace"))
        total += n_chars
        if n_chars > max_source:
            violations.append(
                f"{rel.as_posix()}: {n_chars} chars exceeds the {max_source}-char per-source "
                f"cap. Trim it or split doctrine across scopes."
            )
    if total > max_total:
        violations.append(
            f"repo AGENTS.COMPOSE.md total {total} chars exceeds the {max_total}-char "
            f"budget. Composed context loads every session; keep it lean."
        )
    return violations


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    violations = find_violations(REPO_ROOT)
    if not violations:
        print("agent-compose-size check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(f"\n{len(violations)} agent-compose size violation(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

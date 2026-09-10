#!/usr/bin/env python3
"""Assert AGENTS.md carries the managed workspace-pointer block, never hand-edited.

Regenerates the expected block offline and fails on drift, a missing block, or a
legacy intro line left beside it. No-ops fail-open where it cannot apply: an
unmanaged org, a canonical base that does not point at itself, no root AGENTS.md,
or a symlinked one. See docs/features-agents.md.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn

from agentic_os.config import is_enabled
from agentic_os.generators.generate_agents_pointer import (
    EXEMPT,
    check_drift,
    detect_org_repo,
    is_managed,
)

HOOK_ID = "agents-pointer"
TRACKER = "docs/features-agents.md"

REGEN_HINT = "  regenerate: python3 scripts/apply-agents-pointer.py --repo <name>"


def fail(msgs: list[str]) -> NoReturn:
    for m in msgs:
        print(f"check-{HOOK_ID}: {m}", file=sys.stderr)
    print(REGEN_HINT, file=sys.stderr)
    print(f"  see {TRACKER} for schema", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0

    root = Path.cwd()
    agents = root / "AGENTS.md"
    if not agents.exists() or agents.is_symlink():
        return 0

    org, repo = detect_org_repo(root)
    if (org, repo) in EXEMPT or not is_managed(org, repo):
        return 0

    assert org is not None  # is_managed guarantees a non-None org here
    problems = check_drift(agents.read_text(), org)
    if problems:
        fail(problems)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""pre-commit hook: verify generated seed-skill data is in sync."""

from __future__ import annotations

from agentic_os.generators.generate_seed_skills import check_drift


def main() -> int:
    return check_drift()


if __name__ == "__main__":
    raise SystemExit(main())

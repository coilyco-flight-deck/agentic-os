#!/usr/bin/env python3
"""pre-commit hook: verify the generated caps reference is in sync."""

from __future__ import annotations

from agentic_os.generators.generate_caps_reference import check_drift


def main() -> int:
    return check_drift()


if __name__ == "__main__":
    raise SystemExit(main())

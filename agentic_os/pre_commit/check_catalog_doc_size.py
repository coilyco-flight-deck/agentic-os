#!/usr/bin/env python3
"""Compatibility wrapper for Markdown size discipline.

Markdown size caps now live in check_documentation_layout.py and apply to every
Markdown file, not only the catalog trifecta files.

Usage (when run directly):
    python3 scripts/check-catalog-doc-size.py

Canonical copy lives in coilyco-flight-deck/agentic-os/scripts/. Each consumer repo
gets a stamped copy via agentic-os-kai's apply-catalog-doc-size-hook
rollout. Exits 0 on clean, 1 on any documentation-layout violation.

See docs/catalog-caps-reference.md for the design.
"""
from __future__ import annotations

import sys

from agentic_os.pre_commit.check_documentation_layout import (
    main as documentation_layout_main,
)


def main() -> int:
    return documentation_layout_main()


if __name__ == "__main__":
    sys.exit(main())

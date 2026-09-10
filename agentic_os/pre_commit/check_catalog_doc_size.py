#!/usr/bin/env python3
"""Compatibility wrapper for Markdown size discipline.

Markdown size caps live in check_documentation_layout.py now and apply to every
Markdown file, not only the catalog trifecta. See docs/catalog-caps-reference.md.
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

#!/usr/bin/env python3
"""pre-commit hook: verify agent-compose generated files are in sync."""

from __future__ import annotations

from agentic_os.generators.generate_agent_compose import check_main as main


if __name__ == "__main__":
    raise SystemExit(main())

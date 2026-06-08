#!/usr/bin/env python3
"""Wire the session-pulse SessionStart hook into ~/.claude/settings.json.

Adds one SessionStart hook backed by scripts/session-pulse.sh, which cats
~/.cache/agentic-os/session-pulse.yaml when present and no-ops otherwise.
Any consumer writes that file. The hook is provider-agnostic.

Idempotent: re-runs that find a session-pulse.sh command already registered
make no change. Stdlib only. Run by the claude-hooks ansible role on every host.

Usage:
    scripts/install-session-pulse.py            # write the merged settings
    scripts/install-session-pulse.py --dry-run  # print the result, do not write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
PULSE_SCRIPT = SCRIPT_DIR / "session-pulse.sh"
SETTINGS_PATH = HOME / ".claude" / "settings.json"

SESSIONSTART_CMD = str(PULSE_SCRIPT)
SESSIONSTART_MATCHER = "startup|resume|clear"


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def merge_sessionstart_hook(settings: dict) -> bool:
    """Add the SessionStart hook once. Returns True if it changed anything."""
    hooks = settings.setdefault("hooks", {})
    groups = hooks.setdefault("SessionStart", [])
    for group in groups:
        for hook in group.get("hooks", []):
            if "session-pulse.sh" in hook.get("command", ""):
                return False
    groups.append(
        {
            "matcher": SESSIONSTART_MATCHER,
            "hooks": [{"type": "command", "command": SESSIONSTART_CMD}],
        }
    )
    return True


def write_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    with os.fdopen(fd, "w") as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not PULSE_SCRIPT.exists():
        print(f"error: {PULSE_SCRIPT} not found", file=sys.stderr)
        return 1

    settings = load_settings(SETTINGS_PATH)
    changed = merge_sessionstart_hook(settings)

    if args.dry_run:
        print(json.dumps(settings, indent=2))
        return 0

    if not changed:
        print(f"session-pulse already wired in {SETTINGS_PATH}")
        return 0

    write_settings(SETTINGS_PATH, settings)
    print(f"wrote   {SETTINGS_PATH} (session-pulse SessionStart hook)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

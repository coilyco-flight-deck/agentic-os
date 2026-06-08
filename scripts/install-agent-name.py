#!/usr/bin/env python3
"""Wire the agent self-name into ~/.claude/settings.json.

Installs two surfaces, both backed by scripts/agent-name.sh:
  - statusLine: a persistent footer showing claude-<os>-<hostname>-<tag>.
  - SessionStart hook: injects the same name into the agent's context.

Merge rules, idempotent and conservative:
  - statusLine is set only if absent or already pointing at agent-name.sh.
    A status line the operator set to something else is left untouched.
  - The SessionStart hook is added once; re-runs that find an agent-name.sh
    command already registered make no change.

Stdlib only. Run by the claude-hooks ansible role on every host.

Usage:
    scripts/install-agent-name.py            # write the merged settings
    scripts/install-agent-name.py --dry-run  # print the result, do not write
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
NAME_SCRIPT = SCRIPT_DIR / "agent-name.sh"
SETTINGS_PATH = HOME / ".claude" / "settings.json"

def _cmd(mode: str) -> str:
    """Command string for a given agent-name.sh mode.

    On Windows, Claude Code cannot exec a .sh directly, so the script is run
    through bash (resolved on PATH). Elsewhere the shebang handles it.
    """
    if os.name == "nt":
        return f'bash "{NAME_SCRIPT.as_posix()}" {mode}'
    return f"{NAME_SCRIPT} {mode}"


STATUSLINE_CMD = _cmd("statusline")
SESSIONSTART_CMD = _cmd("sessionstart")
SESSIONSTART_MATCHER = "startup|resume|clear"


def load_settings(path: Path) -> dict:
    """Read settings.json, returning an empty dict if it is absent."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def merge_statusline(settings: dict) -> bool:
    """Set the statusLine block. Returns True if it changed anything."""
    current = settings.get("statusLine")
    if isinstance(current, dict):
        cmd = current.get("command", "")
        if "agent-name.sh" not in cmd and cmd != "":
            print(f"kept existing statusLine ({cmd!r}); not overwriting")
            return False
    desired = {"type": "command", "command": STATUSLINE_CMD, "padding": 2}
    if current == desired:
        return False
    settings["statusLine"] = desired
    return True


def merge_sessionstart_hook(settings: dict) -> bool:
    """Add the SessionStart hook once. Returns True if it changed anything."""
    hooks = settings.setdefault("hooks", {})
    groups = hooks.setdefault("SessionStart", [])
    for group in groups:
        for hook in group.get("hooks", []):
            if "agent-name.sh" in hook.get("command", ""):
                return False
    groups.append(
        {
            "matcher": SESSIONSTART_MATCHER,
            "hooks": [{"type": "command", "command": SESSIONSTART_CMD}],
        }
    )
    return True


def write_settings(path: Path, settings: dict) -> None:
    """Atomically write settings.json."""
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

    if not NAME_SCRIPT.exists():
        print(f"error: {NAME_SCRIPT} not found", file=sys.stderr)
        return 1

    settings = load_settings(SETTINGS_PATH)
    changed = merge_statusline(settings)
    changed = merge_sessionstart_hook(settings) or changed

    if args.dry_run:
        print(json.dumps(settings, indent=2))
        return 0

    if not changed:
        print(f"agent self-name already wired in {SETTINGS_PATH}")
        return 0

    write_settings(SETTINGS_PATH, settings)
    print(f"wrote   {SETTINGS_PATH} (agent self-name: statusLine + SessionStart)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

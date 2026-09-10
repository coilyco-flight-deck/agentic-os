#!/usr/bin/env python3
"""Wire the composed status line and session name into Claude Code.

Installs statusLine and a SessionStart hook. Merge rules are conservative:
statusLine is set only if absent or already managed here, so one the operator set
is left alone, and a host still wired to the retired agent-name.sh is REPOINTED
rather than skipped, since leaving it keeps a deleted script registered on every
converged host.
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
NAME_SCRIPT = SCRIPT_DIR.parent / "docker" / "dev-base" / "session-name.sh"
STATUSLINE_SCRIPT = SCRIPT_DIR.parent / "docker" / "dev-base" / "statusline.sh"
SETTINGS_PATH = HOME / ".claude" / "settings.json"

def _cmd(script: Path, mode: str = "") -> str:
    """Build a cross-platform command string for one shell script.

    On Windows, Claude Code cannot exec a .sh directly, so the script is run
    through bash (resolved on PATH). Elsewhere the shebang handles it.
    """
    suffix = f" {mode}" if mode else ""
    if os.name == "nt":
        return f'bash "{script.as_posix()}"{suffix}'
    return f"{script}{suffix}"


STATUSLINE_CMD = _cmd(STATUSLINE_SCRIPT)
SESSIONSTART_CMD = _cmd(NAME_SCRIPT)
SESSIONSTART_MATCHER = "startup|resume|clear"

# Commands this installer owns and may rewrite. agent-name.sh is the retired
# script; a host converged before its removal still has it registered.
MANAGED_MARKERS = ("agent-name.sh", "session-name.sh")


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
        managed = cmd in {"", STATUSLINE_CMD} or any(m in cmd for m in MANAGED_MARKERS)
        if not managed:
            print(f"kept existing statusLine ({cmd!r}); not overwriting")
            return False
    desired = {"type": "command", "command": STATUSLINE_CMD, "padding": 2}
    if current == desired:
        return False
    settings["statusLine"] = desired
    return True


def merge_sessionstart_hook(settings: dict) -> bool:
    """Add or repoint the SessionStart hook. True if it changed anything."""
    hooks = settings.setdefault("hooks", {})
    groups = hooks.setdefault("SessionStart", [])
    for group in groups:
        for hook in group.get("hooks", []):
            command = hook.get("command", "")
            if not any(marker in command for marker in MANAGED_MARKERS):
                continue
            if command == SESSIONSTART_CMD:
                return False
            hook["command"] = SESSIONSTART_CMD
            return True
    groups.append(
        {
            "matcher": SESSIONSTART_MATCHER,
            "hooks": [{"type": "command", "command": SESSIONSTART_CMD}],
        }
    )
    return True


def write_settings(path: Path, settings: dict) -> Path:
    """Atomically write settings.json, returning the path that took the write."""
    # os.replace swaps a symlink itself, cutting a staged shadow home loose
    # from the host file it points at. See docs/native-shadow.md.
    target = Path(os.path.realpath(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".json")
    with os.fdopen(fd, "w") as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for script in (NAME_SCRIPT, STATUSLINE_SCRIPT):
        if not script.exists():
            print(f"error: {script} not found", file=sys.stderr)
            return 1

    settings = load_settings(SETTINGS_PATH)
    changed = merge_statusline(settings)
    changed = merge_sessionstart_hook(settings) or changed

    if args.dry_run:
        print(json.dumps(settings, indent=2))
        return 0

    if not changed:
        print(f"status line and session name already wired in {os.path.realpath(SETTINGS_PATH)}")
        return 0

    target = write_settings(SETTINGS_PATH, settings)
    print(f"wrote   {target} (provider status line + SessionStart name)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

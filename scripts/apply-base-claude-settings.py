#!/usr/bin/env python3
"""Apply public-safe base preference keys into ~/.claude/settings.json.

Holds the fleet-wide, public-safe Claude Code settings keys that every host
gets regardless of whether the private bridge overlay is present. Today that is
auto-memory off (point-in-time memory drifts and misleads, see the No
auto-memory rule in AGENTS.md), so a host that never checks out the bridge repo
still converges with auto-memory disabled.

Additive and key-scoped: it sets only the keys it owns and preserves every
other key verbatim, so the harness, coily, and the bridge merge can all keep
touching the same file. Idempotent, stdlib only, atomic write. Run by the
claude-hooks ansible role on every host.

Usage:
    scripts/apply-base-claude-settings.py            # write the merged settings
    scripts/apply-base-claude-settings.py --dry-run  # print the result, do not write
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

HOME = Path.home()
SETTINGS_PATH = HOME / ".claude" / "settings.json"

# Public-safe keys applied on every host. Private/personal keys stay in the
# bridge overlay's own merge, never here.
BASE_SETTINGS: dict = {
    "autoMemoryEnabled": False,
}


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def merge_base_settings(settings: dict) -> list[str]:
    """Set each base key when missing or differing. Returns the keys changed."""
    changed = []
    for key, value in BASE_SETTINGS.items():
        if settings.get(key) != value:
            settings[key] = value
            changed.append(key)
    return changed


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

    settings = load_settings(SETTINGS_PATH)
    changed = merge_base_settings(settings)

    if args.dry_run:
        print(json.dumps(settings, indent=2))
        return 0

    if not changed:
        print(f"base settings unchanged in {SETTINGS_PATH}")
        return 0

    write_settings(SETTINGS_PATH, settings)
    print(f"wrote   {SETTINGS_PATH} (base settings: {', '.join(changed)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

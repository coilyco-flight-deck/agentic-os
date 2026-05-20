#!/usr/bin/env python3
"""Render host-specific absolute paths into the tracked Warp config.

Warp does not expand `~` or env vars in `theme.custom.path` or
`background_image.path` (see coilysiren/agentic-os#81). The repo holds the Mac
form as the tracked default. On non-Mac hosts, run this script after every
pull to overwrite the two path lines with the local host's absolute paths.

The rendered changes are then marked `git update-index --skip-worktree` so
they do not show up in `git status` and cannot be committed accidentally.
Mac is the canonical author host and is a no-op.

Touched files:
- warp/settings.toml     [appearance.themes].theme.custom.path
- warp/themes/coilysiren-sombra-wallpaper.yaml   background_image.path

Run with `--unmark` to undo skip-worktree (e.g. to legitimately edit the
canonical Mac form on this host).
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = REPO_ROOT / "warp" / "settings.toml"
THEME_PATH = REPO_ROOT / "warp" / "themes" / "coilysiren-sombra-wallpaper.yaml"
THEME_FILENAME = THEME_PATH.name
WALLPAPER_REL = ("static", "wallpaper.jpg")

TRACKED_FILES = [SETTINGS_PATH, THEME_PATH]


def detect_host() -> str:
    system = platform.system()
    if system == "Darwin":
        return "mac"
    if system == "Windows":
        return "windows"
    if system == "Linux":
        return "linux"
    raise SystemExit(f"unsupported host: {system}")


def warp_themes_dir(host: str) -> Path:
    if host == "mac":
        return Path.home() / ".warp" / "themes"
    if host == "windows":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            raise SystemExit("LOCALAPPDATA not set; cannot resolve Warp themes dir")
        return Path(local_appdata) / "warp" / "Warp" / "config" / "themes"
    return Path.home() / ".config" / "warp-terminal" / "themes"


def wallpaper_path(host: str) -> Path:
    return REPO_ROOT.joinpath(*WALLPAPER_REL)


def toml_str(p: Path) -> str:
    return str(p).replace("\\", "\\\\")


def yaml_str(p: Path) -> str:
    return str(p)


def rewrite_settings(theme_yaml_path: Path) -> bool:
    text = SETTINGS_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(\[appearance\.themes\]\s*\n\s*theme\s*=\s*\{\s*\n\s*custom\s*=\s*\{\s*\n\s*name\s*=\s*"[^"]*",\s*\n\s*path\s*=\s*")[^"]*(",)',
        re.MULTILINE,
    )
    rendered = toml_str(theme_yaml_path)
    new_text, n = pattern.subn(lambda m: m.group(1) + rendered + m.group(2), text)
    if n != 1:
        raise SystemExit(
            f"could not locate theme.custom.path in {SETTINGS_PATH}; "
            "structure may have changed",
        )
    if new_text == text:
        return False
    SETTINGS_PATH.write_text(new_text, encoding="utf-8")
    return True


def rewrite_theme_yaml(wallpaper: Path) -> bool:
    text = THEME_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(background_image:\s*\n\s*path:\s*).*",
        re.MULTILINE,
    )
    rendered = yaml_str(wallpaper)
    new_text, n = pattern.subn(lambda m: m.group(1) + rendered, text)
    if n != 1:
        raise SystemExit(
            f"could not locate background_image.path in {THEME_PATH}",
        )
    if new_text == text:
        return False
    THEME_PATH.write_text(new_text, encoding="utf-8")
    return True


_GIT_CANDIDATES = (
    "git",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files\Git\cmd\git.exe",
    "/usr/bin/git",
    "/opt/homebrew/bin/git",
    "/home/linuxbrew/.linuxbrew/bin/git",
)


def find_git() -> str:
    for candidate in _GIT_CANDIDATES:
        resolved = shutil.which(candidate) if "/" not in candidate and "\\" not in candidate else (candidate if Path(candidate).exists() else None)
        if resolved:
            return resolved
    raise SystemExit("git not found on PATH or in common install locations")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [find_git(), "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def set_skip_worktree(files: list[Path], skip: bool) -> None:
    flag = "--skip-worktree" if skip else "--no-skip-worktree"
    rels = [str(f.relative_to(REPO_ROOT)).replace("\\", "/") for f in files]
    git("update-index", flag, *rels)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--unmark",
        action="store_true",
        help="clear skip-worktree on the rendered files, do not rewrite",
    )
    args = parser.parse_args()

    if args.unmark:
        set_skip_worktree(TRACKED_FILES, skip=False)
        print("cleared skip-worktree on:")
        for f in TRACKED_FILES:
            print(f"  {f}")
        return 0

    host = detect_host()
    if host == "mac":
        print("host is mac; canonical paths already correct, no-op")
        return 0

    themes_dir = warp_themes_dir(host)
    theme_yaml = themes_dir / THEME_FILENAME
    wallpaper = wallpaper_path(host)

    if not wallpaper.exists():
        print(f"warning: wallpaper not found at {wallpaper}", file=sys.stderr)

    changed_settings = rewrite_settings(theme_yaml)
    changed_theme = rewrite_theme_yaml(wallpaper)

    set_skip_worktree(TRACKED_FILES, skip=True)

    print(f"host: {host}")
    print(f"theme yaml path: {theme_yaml}")
    print(f"wallpaper path:  {wallpaper}")
    print(f"settings.toml:   {'rewrote' if changed_settings else 'unchanged'}")
    print(f"theme yaml:      {'rewrote' if changed_theme else 'unchanged'}")
    print("marked skip-worktree on both files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

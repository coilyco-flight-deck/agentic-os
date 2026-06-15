#!/usr/bin/env python3
"""Local release helper: bump version, sign tag, push.

Bumps the latest semver tag (minor by default), rewrites `pyproject.toml`
version and the `DEFAULT_REV` pointer in
`scripts/apply-agentic-os-hooks.py`, commits the bump, creates a signed
annotated tag, and pushes both.

This is the HAND-CUT path, primarily for major bumps and offline releases.
Normal minor releases are automated by `.forgejo/workflows/release.yml`
(tag-bump on every push to main). The version-bump commit here carries a
`[skip ci]` marker so a local run does NOT double-fire that pipeline - the
files are synced and the tag is cut here, and the auto-pipeline stays out
of the way. Non-release pushes resume auto-minor from the tag this cut.
Unlike the auto-pipeline (which advances only DEFAULT_REV via the Contents
API), this path also reconciles pyproject `version` + `uv.lock`, so run it
whenever those drift behind the tags.

Usage:
    python3 scripts/release.py [--bump {major|minor|patch}] [--dry-run]

Bump policy: every release is a minor bump unless --bump says otherwise.
Major is hand-driven only (--bump major) - commit messages are never
parsed to decide the bump.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
APPLY_HOOKS = REPO_ROOT / "scripts" / "apply-agentic-os-hooks.py"
TAG_PREFIX = "v"
VERSION_RE = re.compile(rf"^{TAG_PREFIX}(\d+)\.(\d+)\.(\d+)$")
PYPROJECT_VERSION_RE = re.compile(r'^version = "(\d+\.\d+\.\d+)"$', re.MULTILINE)
DEFAULT_REV_RE = re.compile(r'^DEFAULT_REV = "v\d+\.\d+\.\d+"$', re.MULTILINE)
DEFAULT_BUMP = "minor"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True, capture_output=True, **kwargs)


def latest_tag() -> str | None:
    """Most recent tag matching v<MAJOR>.<MINOR>.<PATCH>, sorted by version."""
    out = run(["git", "tag", "--list", f"{TAG_PREFIX}[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"])
    for line in out.stdout.splitlines():
        if VERSION_RE.match(line.strip()):
            return line.strip()
    return None


def commits_since(tag: str | None) -> list[str]:
    """Return commit subjects since `tag` (or all if None), for the changelog
    and the release-is-empty check. Subjects are not parsed for bump signals."""
    rng = f"{tag}..HEAD" if tag else "HEAD"
    out = run(["git", "log", rng, "--pretty=format:%s"])
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def next_version(prev: str | None, bump: str) -> str:
    if prev is None:
        major, minor, patch = 0, 0, 0
    else:
        m = VERSION_RE.match(prev)
        if not m:
            raise SystemExit(f"latest tag {prev!r} does not parse as semver")
        major, minor, patch = (int(x) for x in m.groups())
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    elif bump == "patch":
        patch += 1
    else:
        raise SystemExit(f"unknown bump {bump!r}")
    return f"{major}.{minor}.{patch}"


def bump_pyproject(new_ver: str) -> bool:
    """Rewrite pyproject.toml version. Returns True if changed."""
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text, n = PYPROJECT_VERSION_RE.subn(f'version = "{new_ver}"', text, count=1)
    if n == 0:
        raise SystemExit("could not find version = \"...\" line in pyproject.toml")
    if new_text == text:
        return False
    PYPROJECT.write_text(new_text, encoding="utf-8")
    return True


def relock() -> bool:
    """Re-resolve uv.lock so its editable self-version tracks pyproject.

    uv.lock pins this package's own version, so a pyproject bump leaves the
    lock a version behind. Untouched, the next `uv run` re-syncs and dirties
    the tree (and `uv run python scripts/release.py` then refuses on its own
    dirty check). Relocking here folds the lock bump into the release commit.
    Returns True when uv.lock changed.
    """
    run(["uv", "lock"])
    out = run(["git", "status", "--porcelain", "uv.lock"])
    return out.stdout.strip() != ""


def bump_default_rev(new_tag: str) -> bool:
    """Rewrite DEFAULT_REV in apply-agentic-os-hooks.py. Returns True if changed."""
    text = APPLY_HOOKS.read_text(encoding="utf-8")
    new_text, n = DEFAULT_REV_RE.subn(f'DEFAULT_REV = "{new_tag}"', text, count=1)
    if n == 0:
        raise SystemExit("could not find DEFAULT_REV line in apply-agentic-os-hooks.py")
    if new_text == text:
        return False
    APPLY_HOOKS.write_text(new_text, encoding="utf-8")
    return True


def working_tree_clean() -> bool:
    out = run(["git", "status", "--porcelain"])
    return out.stdout.strip() == ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", choices=("major", "minor", "patch"), help="Bump to apply. Defaults to minor; pass major for a hand-driven major bump.")
    parser.add_argument("--dry-run", action="store_true", help="Compute and report, do not write.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow uncommitted changes (risky).")
    args = parser.parse_args()

    if not args.allow_dirty and not working_tree_clean():
        print("FAIL: working tree is dirty. Commit or stash first, or pass --allow-dirty.", file=sys.stderr)
        return 1

    prev = latest_tag()
    subjects = commits_since(prev)
    if not subjects and not args.bump:
        print(f"No commits since {prev or 'beginning'}. Nothing to release.")
        return 0

    bump = args.bump or DEFAULT_BUMP

    new_ver = next_version(prev, bump)
    new_tag = f"{TAG_PREFIX}{new_ver}"

    print(f"Previous tag: {prev or '(none)'}")
    print(f"Commits since: {len(subjects)}")
    print(f"Bump: {bump}{'' if args.bump else ' (default)'}")
    print(f"Next version:  {new_tag}")

    if args.dry_run:
        print("Dry run; no changes written.")
        return 0

    changed_files: list[str] = []
    if bump_pyproject(new_ver):
        changed_files.append("pyproject.toml")
    if bump_default_rev(new_tag):
        changed_files.append("scripts/apply-agentic-os-hooks.py")
    if relock():
        changed_files.append("uv.lock")

    if changed_files:
        run(["git", "add", *changed_files])
        # [skip ci] so this hand-cut bump does not double-fire the auto
        # release pipeline (.forgejo/workflows/release.yml) on push.
        run(["git", "commit", "-m", f"chore: bump version to {new_tag} [skip ci]"])
        print(f"Committed version bump touching: {', '.join(changed_files)}")

    summary = subjects[0] if subjects else f"release {new_tag}"
    tag_msg = f"Release {new_tag}: {summary}"
    run(["git", "tag", "-a", "-s", new_tag, "-m", tag_msg])
    print(f"Created signed tag {new_tag}")

    run(["git", "push"])
    run(["git", "push", "--tags"])
    print(f"Pushed commit and tag {new_tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Local release helper: bump version, sign tag, push.

Parses conventional commits since the latest semver tag, computes the next
version per semver rules, bumps `pyproject.toml` version and the
`DEFAULT_REV` pointer in `scripts/apply-agentic-os-hooks.py`, commits the
bump, creates a signed annotated tag, and pushes both.

Local equivalent of the existing GitHub composite action at
`actions/tag-bump/action.yml`, for the no-PR direct-to-main workflow.

Usage:
    python3 scripts/release.py [--bump {major|minor|patch}] [--dry-run]

Conventional-commits semantics:
    BREAKING CHANGE / type!: => major
    feat: / feat(...): => minor
    fix: / fix(...): => patch
    else => no bump (use --bump to force)
"""
from __future__ import annotations

import argparse
import os
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
CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^)]+\))?(?P<bang>!)?:")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True, capture_output=True, **kwargs)


def latest_tag() -> str | None:
    """Most recent tag matching v<MAJOR>.<MINOR>.<PATCH>, sorted by version."""
    out = run(["git", "tag", "--list", f"{TAG_PREFIX}[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"])
    for line in out.stdout.splitlines():
        if VERSION_RE.match(line.strip()):
            return line.strip()
    return None


def commits_since(tag: str | None) -> list[tuple[str, str]]:
    """Return [(subject, body), ...] for commits since `tag` (or all if None)."""
    rng = f"{tag}..HEAD" if tag else "HEAD"
    sep = "\x1e"
    end = "\x1f"
    out = run(["git", "log", rng, f"--pretty=format:%s{sep}%b{end}"])
    entries = []
    for chunk in out.stdout.split(end):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        subject, _, body = chunk.partition(sep)
        entries.append((subject.strip(), body.strip()))
    return entries


def infer_bump(entries: list[tuple[str, str]]) -> str:
    """Walk commits. Major > minor > patch > none."""
    bump = "none"
    for subject, body in entries:
        m = CONVENTIONAL_RE.match(subject)
        if m and m.group("bang"):
            return "major"
        if "BREAKING CHANGE:" in body:
            return "major"
        if m:
            t = m.group("type").lower()
            if t == "feat" and bump in ("none", "patch"):
                bump = "minor"
            elif t == "fix" and bump == "none":
                bump = "patch"
    return bump


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
    parser.add_argument("--bump", choices=("major", "minor", "patch"), help="Override the inferred bump.")
    parser.add_argument("--dry-run", action="store_true", help="Compute and report, do not write.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow uncommitted changes (risky).")
    args = parser.parse_args()

    if not args.allow_dirty and not working_tree_clean():
        print("FAIL: working tree is dirty. Commit or stash first, or pass --allow-dirty.", file=sys.stderr)
        return 1

    prev = latest_tag()
    entries = commits_since(prev)
    if not entries and not args.bump:
        print(f"No commits since {prev or 'beginning'}. Nothing to release.")
        return 0

    inferred = infer_bump(entries)
    bump = args.bump or (inferred if inferred != "none" else None)
    if bump is None:
        print(f"No conventional-commit bump signal in {len(entries)} commit(s) since {prev}. Pass --bump to force.")
        return 0

    new_ver = next_version(prev, bump)
    new_tag = f"{TAG_PREFIX}{new_ver}"

    print(f"Previous tag: {prev or '(none)'}")
    print(f"Commits since: {len(entries)}")
    print(f"Inferred bump: {inferred} (using: {bump})")
    print(f"Next version:  {new_tag}")

    if args.dry_run:
        print("Dry run; no changes written.")
        return 0

    changed_files: list[str] = []
    if bump_pyproject(new_ver):
        changed_files.append("pyproject.toml")
    if bump_default_rev(new_tag):
        changed_files.append("scripts/apply-agentic-os-hooks.py")

    if changed_files:
        run(["git", "add", *changed_files])
        # closes-issue is a working-code discipline. Bump commits are
        # mechanical and have no upstream issue to close.
        env = {**os.environ, "SKIP": "closes-issue"}
        run(["git", "commit", "-m", f"chore: bump version to {new_tag}"], env=env)
        print(f"Committed version bump touching: {', '.join(changed_files)}")

    summary = entries[0][0] if entries else f"release {new_tag}"
    tag_msg = f"Release {new_tag}: {summary}"
    run(["git", "tag", "-a", "-s", new_tag, "-m", tag_msg])
    print(f"Created signed tag {new_tag}")

    run(["git", "push"])
    run(["git", "push", "--tags"])
    print(f"Pushed commit and tag {new_tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

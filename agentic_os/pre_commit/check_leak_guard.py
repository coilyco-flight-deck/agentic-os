#!/usr/bin/env python3
"""Reject plaintext occurrences of awkward-leak terms held only in hex.

Three leak/coupling classes reduce to one primitive: a string S that must not
appear in scope T, where the rule itself is stored encoded so grepping the rule
reveals neither S nor the coupling. leak-guard is that primitive:

  * sensitive data - an employer/partner/personal name that should never be
    grep-bait (`rg <name>` then mail-merge the hits is the threat model);
  * private -> public leaks - a bridge (private) identifier referenced from a
    flight-deck (public) repo, the wrong direction for data lockdown;
  * dependency cycles - one direction of a repo<->repo reference banned to break
    the cycle.

Each rule lives in `leak_guard_rules.py` with its term as lowercase hex, decoded
only in memory here, never written to disk and never printed. A violation
reports the rule id, path, line, and remediation - never the term itself, so the
guard's own output is not a leak. Terms match on word boundaries by default, so
`ward` does not fire on `forward`/`awkward`.

File discovery mirrors the rest of the suite: staged index blobs when a commit
is in flight, every tracked file on `pre-commit run --all-files`. Per-repo opt
paths out via `[tool.agentic-os.leak-guard] excludes = [...]`; per-rule
allowlists (`allow_globs`) live with the rule. Rule scope is matched against the
current repo resolved from `origin`, so a rule fires only where it should.
See docs/leak-guard.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from agentic_os.config import is_enabled, is_excluded, load_excludes
from agentic_os.pre_commit.leak_guard_rules import RULES

HOOK_ID = "leak-guard"
REPO_ROOT = Path.cwd()
# The ruleset module holds hex, not plaintext, so it cannot match - but skip it
# anyway so the guard never scans its own config.
SELF_PATH = "agentic_os/pre_commit/leak_guard_rules.py"


def _git(args: list[str]) -> str:
    """Run a git command, returning trimmed stdout (or '' on failure)."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def _git_lines(args: list[str]) -> list[str]:
    """Run a git command, returning NUL-split nonempty tokens (or [])."""
    out = _git(args)
    return [tok for tok in out.split("\0") if tok] if out else []


def current_repo_name() -> str:
    """Repo slug from origin (worktree-safe), falling back to the toplevel dir."""
    url = _git(["config", "--get", "remote.origin.url"])
    if url:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return slug[:-4] if slug.endswith(".git") else slug
    top = _git(["rev-parse", "--show-toplevel"])
    return Path(top).name if top else ""


def staged_files() -> list[str]:
    """Repo-relative paths staged for commit (added/copied/modified/renamed)."""
    return _git_lines(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"])


def tracked_files() -> list[str]:
    """Every tracked path, used as the `--all-files` fallback."""
    return _git_lines(["ls-files", "-z"])


def _staged_blob(rel: str) -> str | None:
    """The staged (index) content of `rel`, or None if unreadable as text."""
    try:
        raw = subprocess.run(
            ["git", "show", f":{rel}"], capture_output=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _working_text(rel: str) -> str | None:
    """The working-tree content of `rel`, or None if unreadable as text."""
    try:
        return (REPO_ROOT / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _rule_applies(rule: dict, repo: str) -> bool:
    """True if `rule` is in scope for the current `repo`."""
    repos = rule.get("repos")
    return repos is None or repo in repos


def _compile(rule: dict) -> re.Pattern | None:
    """Build the matcher for a rule, decoding its hex term in memory only."""
    try:
        term = bytes.fromhex(rule["term_hex"]).decode("utf-8")
    except (ValueError, UnicodeDecodeError, KeyError):
        sys.stderr.write(f"leak-guard: rule {rule.get('id', '?')!r} has a bad term_hex; skipped\n")
        return None
    pattern = re.escape(term)
    if rule.get("word_boundary", True):
        pattern = rf"\b{pattern}\b"
    flags = 0 if rule.get("case_sensitive", False) else re.IGNORECASE
    return re.compile(pattern, flags)


def scan(rel: str, text: str, rule: dict, matcher: re.Pattern) -> list[str]:
    """Return formatted violations for `rule` in `text` (term never included)."""
    hits: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if matcher.search(line):
            hits.append(f"{rel}:{line_no}: leak-guard[{rule['id']}] - {rule['message']}")
    return hits


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    repo = current_repo_name()
    excludes = load_excludes(HOOK_ID)

    active = [(r, m) for r in RULES if _rule_applies(r, repo) and (m := _compile(r))]
    if not active:
        print(f"{HOOK_ID} check: OK (no rules in scope for {repo or 'this repo'})")
        return 0

    staged = staged_files()
    files, reader = (staged, _staged_blob) if staged else (tracked_files(), _working_text)

    violations: list[str] = []
    for rel in files:
        if rel == SELF_PATH or is_excluded(rel, excludes):
            continue
        text = None
        for rule, matcher in active:
            only = rule.get("only_globs")
            if only and not is_excluded(rel, only):
                continue
            if is_excluded(rel, rule.get("allow_globs", [])):
                continue
            if text is None:
                text = reader(rel)
                if text is None:
                    break
            violations.extend(scan(rel, text, rule, matcher))

    if not violations:
        print(f"{HOOK_ID} check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(
        f"\n{len(violations)} leak-guard violation(s). Encode the term out of "
        f"plaintext (see docs/leak-guard.md) or allowlist a legitimate path.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

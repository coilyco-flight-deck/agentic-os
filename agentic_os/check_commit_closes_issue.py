#!/usr/bin/env python3
"""Require a same-repo Forgejo *URL* closing reference in commit messages.

Wired into each active coilysiren/* repo as a `commit-msg` pre-commit hook
via `scripts/apply-agentic-os-hooks.py`. Canonical copy lives here in
agentic-os; consumers reference this repo at a pinned `rev:` in their
`.pre-commit-config.yaml` and pre-commit pip-installs the package.

Why URL-only (coilysiren/agentic-os-kai#496): a bare `closes #N` (or the short
`owner/repo#N`) is a GitHub closing keyword too. Repos that mirror to GitHub
have those refs re-interpreted on the GitHub side at push time, silently
closing whatever GitHub issue happens to hold number N - a different tracker
than the canonical Forgejo one. The full Forgejo URL is the only form GitHub
does not auto-close from, so it is the only accepted form.

Accepted (case-insensitive), the issue must live in THIS repo:
    closes  https://forgejo.coilysiren.me/<this-owner>/<this-repo>/issues/N
    fixes   https://forgejo.coilysiren.me/<this-owner>/<this-repo>/issues/N
    resolves https://forgejo.coilysiren.me/<this-owner>/<this-repo>/issues/N
    (close/closed/fix/fixed/resolve/resolved all accepted)

Rejected:
    - bare `closes #N` and short `closes owner/repo#N` (GitHub-auto-close risk)
    - a Forgejo URL pointing at a different owner/repo
    - no closing reference at all

Exempt: Merge / Revert / fixup! / squash! commits.

Exits 0 on accept, 1 on reject (with a dictation-friendly error that names
the fix to apply from a phone).
"""

from __future__ import annotations

import re
import subprocess
import sys

KEYWORD = r"close[sd]?|fix(?:e[sd])?|resolve[sd]?"
FORGEJO_HOST = "forgejo.coilysiren.me"

# The one accepted form: a keyword plus a full Forgejo issue URL.
URL_RE = re.compile(
    rf"\b(?:{KEYWORD})\s+"
    rf"https?://{re.escape(FORGEJO_HOST)}/"
    r"(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/issues/\d+",
    re.IGNORECASE,
)

# Short forms we explicitly reject (bare #N or owner/repo#N) - these are what
# GitHub auto-closes from. Detected only to emit a targeted error message.
SHORT_RE = re.compile(
    rf"\b(?:{KEYWORD})\s+(?P<qualifier>[\w.-]+/[\w.-]+)?#\d+",
    re.IGNORECASE,
)

EXEMPT_PREFIXES = ("Merge ", "Revert ", "fixup! ", "squash! ")

ERROR_NO_REF = (
    "ERROR: commit message must close an issue in this repo via its Forgejo URL.\n"
    "  Add 'closes https://forgejo.coilysiren.me/<owner>/<repo>/issues/N'\n"
    "  (fixes / resolves also accepted).\n"
    "  File the issue in this repo first if one does not exist:\n"
    "  https://forgejo.coilysiren.me/coilysiren/<repo>/issues/new\n"
)
ERROR_SHORT_FORM = (
    "ERROR: bare 'closes #N' / 'owner/repo#N' is rejected.\n"
    "  Those are GitHub closing keywords too: on a repo that mirrors to\n"
    "  GitHub they silently close whatever GitHub issue holds number N,\n"
    "  a different tracker than canonical Forgejo (agentic-os-kai#496).\n"
    "  Use the full Forgejo URL instead:\n"
    "  closes https://forgejo.coilysiren.me/<owner>/<repo>/issues/N\n"
)
ERROR_WRONG_REPO = (
    "ERROR: the Forgejo issue URL points at a different repo.\n"
    "  The closing reference must be an issue in THIS repo. File it here\n"
    "  first and link that URL.\n"
)
REMOTE_RE = re.compile(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")


def this_repo() -> tuple[str, str] | None:
    """Return (owner, repo) lowercased from git remote 'origin', or None."""
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    m = REMOTE_RE.search(out)
    if not m:
        return None
    return (m.group(1).lower(), m.group(2).lower())


def classify(body: str, this: tuple[str, str] | None) -> str:
    """Return 'ok', 'wrong-repo', 'short-form', or 'none'.

    'ok' requires a Forgejo issue URL whose repo NAME matches this repo. The
    owner is intentionally ignored: repos mid org-split have a GitHub origin
    owner (e.g. coilyco-flight-deck/<name>) that differs from the canonical
    Forgejo tracker owner (coilysiren/<name>), and the anti-GitHub-auto-close
    safety goal does not depend on owner anyway (agentic-os-kai#496, #534). A
    URL for a different repo name yields 'wrong-repo'. Absent any URL, a short
    `#N` / `owner/repo#N` ref yields 'short-form'; otherwise 'none'.
    """
    saw_url_other_repo = False
    for match in URL_RE.finditer(body):
        repo = match.group("repo").lower()
        if this is None or repo == this[1]:
            return "ok"
        saw_url_other_repo = True
    if saw_url_other_repo:
        return "wrong-repo"
    if SHORT_RE.search(body):
        return "short-form"
    return "none"


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        sys.stderr.write("usage: check-commit-closes-issue <commit-msg-file>\n")
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        raw = fh.read()
    body = re.sub(r"(?m)^#.*\n?", "", raw).strip()
    if not body:
        return 0
    first_line = body.split("\n", 1)[0]
    if first_line.startswith(EXEMPT_PREFIXES):
        return 0

    verdict = classify(body, this_repo())
    if verdict == "ok":
        return 0
    if verdict == "short-form":
        sys.stderr.write(ERROR_SHORT_FORM)
    elif verdict == "wrong-repo":
        sys.stderr.write(ERROR_WRONG_REPO)
    else:
        sys.stderr.write(ERROR_NO_REF)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Tests for the dev-base agent-name.sh `gitidentity` mode (agentic-os#244).

A warded agent stamps its self-name as the git author/committer NAME at session
start so a commit records which agent made it, while the load-bearing bot EMAIL
(set by ward at --system) is left untouched so Forgejo still links the commit to
the coilyco-ops account. These drive the baked container script via subprocess.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "docker" / "dev-base" / "agent-name.sh"
PAYLOAD = '{"session_id":"AbC123xyz"}'


def _run(mode: str, home: Path) -> str:
    # A fresh HOME isolates --global writes/reads to this test's gitconfig, and
    # TMPDIR isolates the per-session name cache so runs never cross-talk.
    proc = subprocess.run(
        [str(SCRIPT), mode],
        input=PAYLOAD,
        capture_output=True,
        text=True,
        check=True,
        env={"HOME": str(home), "TMPDIR": str(home), "PATH": "/usr/bin:/bin"},
    )
    return proc.stdout.strip()


def _git_global(key: str, home: Path) -> str:
    proc = subprocess.run(
        ["git", "config", "--global", "--get", key],
        capture_output=True,
        text=True,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
    )
    return proc.stdout.strip()  # empty string when unset (exit 1 ignored)


def test_gitidentity_sets_user_name_to_self_name(tmp_path: Path) -> None:
    name = _run("statusline", tmp_path)
    assert name.startswith("claude-")  # sanity: the derived self-name

    _run("gitidentity", tmp_path)
    assert _git_global("user.name", tmp_path) == name


def test_gitidentity_leaves_email_untouched(tmp_path: Path) -> None:
    # The email is load-bearing for Forgejo account linking; gitidentity must
    # never write it, so it falls through to ward's --system bot address.
    _run("gitidentity", tmp_path)
    assert _git_global("user.email", tmp_path) == ""


def test_gitidentity_is_idempotent(tmp_path: Path) -> None:
    _run("gitidentity", tmp_path)
    first = _git_global("user.name", tmp_path)
    _run("gitidentity", tmp_path)
    assert _git_global("user.name", tmp_path) == first

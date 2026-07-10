"""Smoke coverage for the WARD_CONFIG_REF propagation path."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WARD_REF_PREFIX = "forgejo.coilysiren.me/coilyco-flight-deck/agentic-os@"


def _git_head(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def _foreign_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "foreign"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "foreign"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return repo


def test_common_shell_uses_the_canonical_checkout_instead_of_cwd(tmp_path: Path) -> None:
    foreign = _foreign_repo(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "PATH": "/usr/bin:/bin",
            "AOS_REPO_ROOT": "",
        }
    )
    proc = subprocess.run(
        [
            "bash",
            "-lc",
            f'source "{REPO_ROOT / "shell" / "common.sh"}"; printf "%s" "$WARD_CONFIG_REF"',
        ],
        cwd=foreign,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.stdout == f"{WARD_REF_PREFIX}{_git_head(REPO_ROOT)}//.ward"


def test_container_entrypoint_seeds_the_read_only_surface_env(tmp_path: Path) -> None:
    foreign = _foreign_repo(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "PATH": "/usr/bin:/bin",
        }
    )
    entrypoint = REPO_ROOT / "docker" / "dev-base" / "ward-shell-entrypoint.sh"
    proc = subprocess.run(
        [
            "bash",
            str(entrypoint),
            "bash",
            "-lc",
            'printf "%s\n%s" "$AOS_REPO_ROOT" "$WARD_CONFIG_REF"',
        ],
        cwd=foreign,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    root, ref = proc.stdout.splitlines()
    assert root == str(REPO_ROOT)
    assert ref == f"{WARD_REF_PREFIX}{_git_head(REPO_ROOT)}//.ward"

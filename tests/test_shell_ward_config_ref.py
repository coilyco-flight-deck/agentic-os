"""Smoke coverage for the WARD_CONFIG_REF propagation path."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _bundle_dir_of(ref: str) -> Path:
    """Resolve a file:// WARD_CONFIG_REF back to the checkout it points into."""
    assert ref.startswith("file://"), ref
    assert ref.endswith("/.ward"), ref
    return Path(ref[len("file://"):].removesuffix("/.ward")).resolve()


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
            "FORGEJO_WORKSPACE": str(REPO_ROOT),
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

    # Host shells point at the canonical checkout's bundle live (file://), so a
    # pull is immediately effective and launch needs no gitsync or credentials.
    assert _bundle_dir_of(proc.stdout) == REPO_ROOT.resolve()


def test_container_entrypoint_seeds_the_read_only_surface_env(tmp_path: Path) -> None:
    foreign = _foreign_repo(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "PATH": "/usr/bin:/bin",
            "FORGEJO_WORKSPACE": str(REPO_ROOT),
            "WARD_READONLY": "1",
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
    # The entrypoint reads the seeded checkout's bundle live too - no in-container
    # gitsync, credentials, or config-bundle cache (the ward#1086 FETCH_HEAD class).
    assert ref == f"file://{root}/.ward"

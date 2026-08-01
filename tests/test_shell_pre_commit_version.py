"""Behavioral coverage for the shared-shell aos-precommit tag diagnostic."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_SH = REPO_ROOT / "shell" / "common.sh"


def _write_consumer(root: Path, name: str, rev: str) -> None:
    repo = root / "coilyco-flight-deck" / name
    repo.mkdir(parents=True)
    (repo / ".pre-commit-config.yaml").write_text(
        "repos:\n"
        "  - repo: https://forgejo.example/coilyco-flight-deck/agentic-os\n"
        f"    rev: {rev}\n",
        encoding="utf-8",
    )


def _write_yq_stub(path: Path) -> None:
    path.write_text(
        "#!/bin/sh\n"
        "sed -n 's/^[[:space:]]*rev:[[:space:]]*//p' \"$3\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_outdated_diagnostic_compares_full_release_tags(tmp_path: Path) -> None:
    aos_repo = tmp_path / "aos"
    subprocess.run(
        ["git", "init", str(aos_repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(aos_repo), "commit", "--allow-empty", "-m", "initial"],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    for tag in (
        "aos-precommit-v0.8.0",
        "aos-precommit-v0.9.0",
        "aos-precommit-v9.9.9-invalid",
    ):
        subprocess.run(
            ["git", "-c", "tag.gpgSign=false", "-C", str(aos_repo), "tag", tag],
            check=True,
            capture_output=True,
            text=True,
        )
    (aos_repo / "pyproject.toml").write_text(
        '[project]\nversion = "0.1.0"\n',
        encoding="utf-8",
    )

    projects = tmp_path / "projects"
    _write_consumer(projects, "current", "aos-precommit-v0.9.0")
    _write_consumer(projects, "stale", "aos-precommit-v0.8.0")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_yq_stub(bin_dir / "yq")

    command = " ".join(
        (
            f"source {shlex.quote(str(COMMON_SH))}",
            "&&",
            "pre-commit-all-aos-version-outdated",
        )
    )
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-c", command],
        cwd=projects,
        env={
            **os.environ,
            "AOS_REPO_ROOT": str(aos_repo),
            "HOME": str(tmp_path / "home"),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "PROJECTS_ROOT": str(projects),
            "_SIREN_SHELL_ENV": "1",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "coilyco-flight-deck/stale\t"
        "aos-precommit-v0.8.0\t"
        "aos-precommit-v0.9.0\n"
    )

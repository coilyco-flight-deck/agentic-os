"""Tests for the compiled-residency status-line provider."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


PROVIDER = (
    Path(__file__).resolve().parents[1]
    / "docker"
    / "dev-base"
    / "statusline.d"
    / "20-repos.sh"
)


def run_provider(tmp_path: Path, residency: list[str], checkouts: list[str]) -> str:
    projects = tmp_path / "projects"
    for identity in checkouts:
        (projects / identity / ".git").mkdir(parents=True)
    fleet = tmp_path / "fleet-orgs.txt"
    fleet.write_text(
        "\n".join(sorted({identity.split("/", 1)[0] for identity in checkouts})) + "\n",
        encoding="utf-8",
    )
    binary = tmp_path / "bin" / "aos"
    binary.parent.mkdir()
    binary.write_text(
        "#!/bin/sh\nprintf '%s\\n' "
        + " ".join(f"'{identity}'" for identity in residency)
        + "\n",
        encoding="utf-8",
    )
    binary.chmod(0o755)
    environment = dict(os.environ)
    environment.update(
        {
            "AOS_BIN": str(binary),
            "AOS_FLEET_ORGS": str(fleet),
            "AOS_REPOS_ROOT": str(projects),
            "HOME": str(tmp_path),
        }
    )
    result = subprocess.run(
        ["bash", str(PROVIDER)],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    return result.stdout


def test_repo_tracker_matches_full_repository_identity(tmp_path: Path) -> None:
    output = run_provider(
        tmp_path,
        ["owner-one/shared"],
        ["owner-one/shared", "owner-two/shared"],
    )
    assert "1 to remove: owner-two/shared" in output


def test_repo_tracker_reports_all_clear_for_residency(tmp_path: Path) -> None:
    output = run_provider(tmp_path, ["owner/one"], ["owner/one"])
    assert "1 repos, none stray" in output

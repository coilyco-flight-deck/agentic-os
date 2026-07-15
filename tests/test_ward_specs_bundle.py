from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_repos_bundle_owns_landing_policy() -> None:
    repos = (ROOT / ".ward" / "repos.kdl").read_text(encoding="utf-8")
    assert 'workflow default="merge-remote-main"' in repos
    assert 'repo "coilyco-flight-deck/agentic-os" workflow="pull-request-and-merge"' in repos
    assert not (ROOT / ".ward" / "workflow.kdl").exists()

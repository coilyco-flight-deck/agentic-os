from __future__ import annotations

import pathlib

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".forgejo" / "workflows"


def unconditional_run_commands(workflow: dict) -> set[str]:
    """Commands a workflow always runs, so conditional alert and PR-only steps drop out."""
    commands = set()
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if "run" in step and "if" not in step:
                commands.add(" ".join(step["run"].split()))
    return commands


def test_promote_workflow_runs_every_gate_ci_runs() -> None:
    # ci.yml deliberately never re-gates the release branch, trusting that promote
    # already ran the suite. A narrower promote gate silently promotes a red main.
    ci = yaml.safe_load((WORKFLOWS / "ci.yml").read_text())
    promote = yaml.safe_load((WORKFLOWS / "promote.yml").read_text())
    missing = unconditional_run_commands(ci) - unconditional_run_commands(promote)
    assert not missing, f"promote.yml skips gating steps ci.yml runs: {sorted(missing)}"


def test_promote_workflow_uses_the_same_repo_gate_as_ci() -> None:
    workflow = (WORKFLOWS / "promote.yml").read_text()
    gate = (ROOT / "scripts" / "ci" / "repo-test-gate.sh").read_text()
    assert "name: promote" in workflow
    assert "scripts/ci/repo-test-gate.sh" in workflow
    assert "uv run pytest" in gate
    assert "pre-commit run --all-files" in gate
    assert "install-workflow-ward.sh" not in workflow
    assert "Load the .ward bundle with the updated ward" not in workflow
    assert "ward exec test" not in workflow
    assert "Install ward from source with workflow bundle support" not in workflow

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_ward_doctor() -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "WARD_CONFIG_REF": f"file://{ROOT}/.ward",
            "WARD_DOCTOR_ALLOW_PLACEHOLDERS": "1",
        }
    )
    return subprocess.run(
        ["ward", "doctor"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def test_repos_bundle_is_accepted_by_ward_doctor() -> None:
    result = _run_ward_doctor()
    assert "ward doctor: all checks passed" in result.stdout


def test_repos_bundle_does_not_ship_a_separate_workflow_overlay() -> None:
    assert not (ROOT / ".ward" / "workflow.kdl").exists()

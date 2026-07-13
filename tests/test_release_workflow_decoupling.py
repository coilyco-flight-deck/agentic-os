"""Tests for the release job graph: the tag never waits on the image publish (aos#490)."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = (
    Path(__file__).resolve().parent.parent / ".forgejo" / "workflows" / "release.yml"
)


def _jobs() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


def test_release_job_needs_plan_release_only() -> None:
    needs = _jobs()["release"]["needs"]
    if isinstance(needs, str):
        needs = [needs]
    assert needs == ["plan-release"]


def test_publish_dev_base_runs_after_the_tag() -> None:
    needs = _jobs()["publish-dev-base"]["needs"]
    if isinstance(needs, str):
        needs = [needs]
    assert "release" in needs


def test_every_release_job_carries_a_telegram_alert_with_retries() -> None:
    text = WORKFLOW.read_text()
    assert text.count("Alert Telegram on main failure") == len(_jobs())
    assert text.count("telegram alert attempt {attempt}/{ATTEMPTS} failed") == len(_jobs())

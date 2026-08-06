"""Tests for role context measurement reports."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_os.context_budget_role import FORMAT
from agentic_os.generators import generate_context_budget_role_reports as reports


def _snapshot(
    role: str,
    *,
    eager: int,
    lazy: int,
    composed: int,
) -> dict[str, object]:
    return {
        "format": FORMAT,
        "subject": {"role": role},
        "bundle": {"format": "agent-compose.bundle"},
        "totals": {
            "eager": {"components": 1, "bytes": eager * 4, "tokens": eager},
            "lazy": {"components": 1, "bytes": lazy * 4, "tokens": lazy},
        },
        "breakdown": {
            "eager": {
                "role-composed-frontmatter": {
                    "components": composed,
                    "bytes": 0,
                    "tokens": 0,
                }
            },
            "lazy": {},
        },
        "components": {"eager": {}, "lazy": {}},
        "skills": {},
    }


def _write_snapshot(docs_dir: Path, role: str = "content") -> Path:
    path = docs_dir / f"context-budget-{role}-current.yaml"
    path.write_text(
        json.dumps(_snapshot(role, eager=80, lazy=120, composed=3)),
        encoding="utf-8",
    )
    return path


def test_loads_canonical_roles_from_launch_profiles(tmp_path: Path) -> None:
    profiles = tmp_path / "harness-launch-profiles.yaml"
    profiles.write_text(
        "roles:\n  engineer:\n    agent: codex\n  ops:\n    agent: claude\n",
        encoding="utf-8",
    )

    assert reports.load_canonical_roles(profiles) == ("engineer", "ops")


def test_render_lists_one_harness_neutral_snapshot_per_role(tmp_path: Path) -> None:
    _write_snapshot(tmp_path)
    built = reports.build_reports(tmp_path, roles=("content",))
    rendered = built[tmp_path / "context-budget-role-current.md"]
    flat = " ".join(rendered.split())

    assert "one harness-neutral snapshot" in rendered
    assert "[Content Manager](context-budget-content-current.yaml)" in rendered
    assert "eager 80, lazy 120, composed 3" in flat
    assert "Claude" not in rendered
    assert "Codex" not in rendered
    assert "low-context" not in rendered


def test_generate_then_check_drift(tmp_path: Path) -> None:
    _write_snapshot(tmp_path)
    assert reports.generate(tmp_path, roles=("content",)) == 0
    assert reports.check_drift(tmp_path, roles=("content",)) == 0

    report = tmp_path / "context-budget-role-current.md"
    report.write_text("# stale\n", encoding="utf-8")
    assert reports.check_drift(tmp_path, roles=("content",)) == 1


def test_rejects_snapshot_subject_drift(tmp_path: Path) -> None:
    path = _write_snapshot(tmp_path)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["subject"]["seat"] = "codex"
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    with pytest.raises(RuntimeError, match="subject must name exactly one role"):
        reports.build_reports(tmp_path, roles=("content",))


def test_rejects_malformed_snapshot(tmp_path: Path) -> None:
    path = _write_snapshot(tmp_path)
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unsupported role context snapshot"):
        reports.build_reports(tmp_path, roles=("content",))


def test_rejects_missing_role_snapshot(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="roles have no current snapshot: content"):
        reports.build_reports(tmp_path, roles=("content",))


def test_committed_role_report_is_current() -> None:
    assert reports.check_drift() == 0

"""Tests for generated frontier-to-low-context role budget diffs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_os.context_budget_role_seat import FORMAT
from agentic_os.generators import generate_context_budget_role_reports as reports

TEST_LAYOUTS = {
    "cloud-a": "frontier",
    "cloud-b": "frontier",
    "oss-a": "low-context",
    "oss-b": "low-context",
}


def _snapshot(
    role: str,
    seat: str,
    model_class: str,
    *,
    eager: int,
    lazy: int,
    composed: int,
) -> dict[str, object]:
    return {
        "format": FORMAT,
        "subject": {"role": role, "seat": seat},
        "bundle": {"model_class": model_class},
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


def _write_snapshots(
    docs_dir: Path,
    *,
    wrong_class_seat: str | None = None,
) -> dict[str, str]:
    layouts = TEST_LAYOUTS
    frontier_index = 0
    for seat, model_class in layouts.items():
        if model_class == "frontier":
            eager = 100 + frontier_index * 10
            frontier_index += 1
        else:
            eager = 80
        snapshot = _snapshot(
            "social",
            seat,
            (
                "low-context"
                if seat == wrong_class_seat and model_class == "frontier"
                else model_class
            ),
            eager=eager,
            lazy=200 if model_class == "frontier" else 120,
            composed=5 if model_class == "frontier" else 3,
        )
        path = docs_dir / f"context-budget-social-{seat}-current.yaml"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
    return layouts


def test_render_computes_class_envelope_diff(tmp_path: Path) -> None:
    layouts = _write_snapshots(tmp_path)
    built = reports.build_reports(tmp_path, roles=("social",), layouts=layouts)
    rendered = built[tmp_path / "context-budget-role-social-current.md"]

    assert "**Frontier social**" in rendered
    assert "**Low-context social**" in rendered
    assert "eager saves 20 to 30 tokens" in rendered
    assert "lazy saves 80 tokens" in rendered
    assert "composed sources 5 -> 3" in rendered


def test_generate_then_check_drift(tmp_path: Path) -> None:
    layouts = _write_snapshots(tmp_path)
    assert reports.generate(tmp_path, roles=("social",), layouts=layouts) == 0
    assert reports.check_drift(tmp_path, roles=("social",), layouts=layouts) == 0

    report = tmp_path / "context-budget-role-social-current.md"
    report.write_text("# stale\n", encoding="utf-8")
    assert reports.check_drift(tmp_path, roles=("social",), layouts=layouts) == 1


def test_rejects_snapshot_model_class_drift(tmp_path: Path) -> None:
    layouts = TEST_LAYOUTS
    frontier_seat = next(
        seat for seat, model_class in layouts.items() if model_class == "frontier"
    )
    _write_snapshots(tmp_path, wrong_class_seat=frontier_seat)

    with pytest.raises(RuntimeError, match="expected model class"):
        reports.build_reports(tmp_path, roles=("social",), layouts=layouts)


def test_frontier_only_role_omits_low_context_diff(tmp_path: Path) -> None:
    for seat in ("cloud-a", "cloud-b"):
        snapshot = _snapshot(
            "ceo",
            seat,
            "frontier",
            eager=100,
            lazy=200,
            composed=5,
        )
        path = tmp_path / f"context-budget-ceo-{seat}-current.yaml"
        path.write_text(json.dumps(snapshot), encoding="utf-8")

    built = reports.build_reports(tmp_path, roles=("ceo",), layouts=TEST_LAYOUTS)
    rendered = built[tmp_path / "context-budget-role-ceo-current.md"]

    assert "**Frontier ceo**" in rendered
    assert "**Low-context ceo**" not in rendered
    assert "Low-context diff" not in rendered
    assert "Only frontier snapshots are available" in rendered


def test_committed_role_reports_are_current() -> None:
    assert reports.check_drift() == 0

"""Tests for policy-scoped role context-budget reports."""
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
        declared_class = model_class
        if seat == wrong_class_seat:
            declared_class = (
                "low-context" if model_class == "frontier" else "frontier"
            )
        snapshot = _snapshot(
            "content",
            seat,
            declared_class,
            eager=eager,
            lazy=200 if model_class == "frontier" else 120,
            composed=5 if model_class == "frontier" else 3,
        )
        path = docs_dir / f"context-budget-content-{seat}-current.yaml"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
    return layouts


def test_render_computes_class_envelope_diff(tmp_path: Path) -> None:
    layouts = _write_snapshots(tmp_path)
    built = reports.build_reports(tmp_path, roles=("content",), layouts=layouts)
    rendered = built[tmp_path / "context-budget-role-content-current.md"]

    assert "**Frontier Content Manager**" in rendered
    assert "**Low-context Content Manager**" in rendered
    assert "eager saves 20 to 30 tokens" in rendered
    assert "lazy saves 80 tokens" in rendered
    assert "composed sources 5 -> 3" in rendered
    assert "all AOS-supported model classes" in rendered


def test_generate_then_check_drift(tmp_path: Path) -> None:
    layouts = _write_snapshots(tmp_path)
    assert reports.generate(tmp_path, roles=("content",), layouts=layouts) == 0
    assert reports.check_drift(tmp_path, roles=("content",), layouts=layouts) == 0

    report = tmp_path / "context-budget-role-content-current.md"
    report.write_text("# stale\n", encoding="utf-8")
    assert reports.check_drift(tmp_path, roles=("content",), layouts=layouts) == 1


def test_rejects_excluded_snapshot_model_class_drift(tmp_path: Path) -> None:
    layouts = TEST_LAYOUTS
    low_context_seat = next(
        seat for seat, model_class in layouts.items() if model_class == "low-context"
    )
    _write_snapshots(tmp_path, wrong_class_seat=low_context_seat)

    with pytest.raises(RuntimeError, match="expected model class"):
        reports.build_reports(
            tmp_path,
            roles=("content",),
            layouts=layouts,
            inventory_model_classes={"content": ["frontier"]},
        )


def test_rejects_malformed_excluded_snapshot(tmp_path: Path) -> None:
    layouts = _write_snapshots(tmp_path)
    excluded = tmp_path / "context-budget-content-oss-a-current.yaml"
    excluded.write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unsupported role-seat context snapshot"):
        reports.build_reports(
            tmp_path,
            roles=("content",),
            layouts=layouts,
            inventory_model_classes={"content": ["frontier"]},
        )


def test_frontier_only_policy_omits_valid_low_context_snapshots(
    tmp_path: Path,
) -> None:
    layouts = _write_snapshots(tmp_path)
    built = reports.build_reports(
        tmp_path,
        roles=("content",),
        layouts=layouts,
        inventory_model_classes={"content": ["frontier"]},
    )
    rendered = built[tmp_path / "context-budget-role-content-current.md"]

    assert "**Frontier Content Manager**" in rendered
    assert "**Low-context Content Manager**" not in rendered
    assert "Low-context diff" not in rendered
    assert "intentionally measures frontier seats only" in rendered
    assert "Only frontier snapshots are available" not in rendered
    assert (tmp_path / "context-budget-content-oss-a-current.yaml").exists()

    inventory = built[tmp_path / "context-budget-role-seat-current.md"]
    assert (
        "Aggregate measurement scope is separate from runtime compatibility"
        in inventory
    )
    assert "context-budget-role-content-current.md" in inventory
    assert "frontier only." in inventory


@pytest.mark.parametrize(
    ("policy", "message"),
    [
        ({"unknown": ["frontier"]}, "unknown role"),
        ({"content": ["unknown"]}, "unsupported classes"),
        ({"content": []}, "at least one class"),
        ({"content": ["frontier", "frontier"]}, "duplicate classes"),
    ],
)
def test_inventory_policy_fails_closed(
    tmp_path: Path,
    policy: dict[str, list[str]],
    message: str,
) -> None:
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "format": reports.INVENTORY_POLICY_FORMAT,
                "inventory_model_classes": policy,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=message):
        reports.load_inventory_model_classes(
            policy_path,
            roles=("content",),
            model_classes=reports.MODEL_CLASSES,
        )


def test_inventory_scope_requires_a_frontier_snapshot(tmp_path: Path) -> None:
    layouts = _write_snapshots(tmp_path)

    with pytest.raises(RuntimeError, match="no frontier snapshot after inventory"):
        reports.build_reports(
            tmp_path,
            roles=("content",),
            layouts=layouts,
            inventory_model_classes={"content": ["low-context"]},
        )


def test_committed_role_reports_are_current() -> None:
    assert reports.check_drift() == 0

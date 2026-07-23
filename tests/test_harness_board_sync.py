from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from agentic_os import harness_board_sync


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "harness_board"


@pytest.fixture
def board_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    aosh_root = tmp_path / "aosh"
    shutil.copytree(FIXTURE_ROOT, aosh_root)
    roles_path = aosh_root / "roles.kdl"
    ward_roles_path = tmp_path / "ward-roles.kdl"
    ward_roles_path.write_text(roles_path.read_text(encoding="utf-8"), encoding="utf-8")
    return aosh_root, roles_path, ward_roles_path


def _rewrite_yaml(path: Path, mutate: Callable[[dict[str, object]], None]) -> None:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    mutate(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_fixture_renders_deterministic_model_opaque_projection(
    board_sources: tuple[Path, Path, Path],
) -> None:
    aosh_root, roles_path, _ = board_sources

    board = harness_board_sync.load_board(aosh_root, roles_path=roles_path)
    rendered = harness_board_sync.render_board(board)
    rendered_ward = harness_board_sync.render_ward_board(board)

    payload = json.loads(rendered)
    assert payload["roles"] == [
        {
            "role": route.role,
            "intents": [
                {"intent": lane.intent, "harness": lane.harness}
                for lane in route.lanes
            ],
        }
        for route in board.roles
    ]
    for route in board.roles:
        assert f"    role {route.role} {{" in rendered_ward
        for lane in route.lanes:
            assert f"        intent {lane.intent} {{" in rendered_ward
            assert f"            harness {lane.harness}" in rendered_ward
    assert not {"model", "server", "fallback", "orchestrator", "rationale"} & set(
        rendered.split('"')
    )
    assert not {"model", "server", "fallback", "orchestrator", "rationale"} & set(
        rendered_ward.replace("{", " ").replace("}", " ").split()
    )


@pytest.mark.parametrize("drift_target", ["json", "ward-kdl"])
def test_check_reports_drift_without_writing(
    board_sources: tuple[Path, Path, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    drift_target: str,
) -> None:
    aosh_root, roles_path, ward_roles_path = board_sources
    board = harness_board_sync.load_board(aosh_root, roles_path=roles_path)
    output = tmp_path / "role-harnesses.json"
    output.write_text(harness_board_sync.render_board(board), encoding="utf-8")
    if drift_target == "json":
        output.write_text("{}\n", encoding="utf-8")
        current_ward_roles = ward_roles_path.read_text(encoding="utf-8")
        ward_roles_path.write_text(
            harness_board_sync.merge_ward_board(
                current_ward_roles,
                harness_board_sync.render_ward_board(board),
                ward_roles_path,
            ),
            encoding="utf-8",
        )
    original_output = output.read_text(encoding="utf-8")
    original_ward_roles = ward_roles_path.read_text(encoding="utf-8")

    assert (
        harness_board_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
            ward_roles_path=ward_roles_path,
            check=True,
        )
        == 1
    )
    assert output.read_text(encoding="utf-8") == original_output
    assert ward_roles_path.read_text(encoding="utf-8") == original_ward_roles
    stderr = capsys.readouterr().err
    expected_drift = output if drift_target == "json" else ward_roles_path
    assert f"drift: {expected_drift}" in stderr


def test_sync_writes_then_check_passes(
    board_sources: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    aosh_root, roles_path, ward_roles_path = board_sources
    output = tmp_path / "role-harnesses.json"

    assert (
        harness_board_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
            ward_roles_path=ward_roles_path,
            check=False,
        )
        == 0
    )
    projected_roles = ward_roles_path.read_text(encoding="utf-8")
    assert projected_roles.startswith("roles {\n")
    assert projected_roles.count(harness_board_sync.KDL_BEGIN) == 1
    board = harness_board_sync.load_board(aosh_root, roles_path=roles_path)
    first_lane = board.roles[0].lanes[0]
    assert f"intent {first_lane.intent} {{" in projected_roles
    assert f"harness {first_lane.harness}" in projected_roles
    assert (
        harness_board_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
            ward_roles_path=ward_roles_path,
            check=True,
        )
        == 0
    )


def test_if_present_skips_only_an_absent_checkout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing-aosh"

    assert (
        harness_board_sync.main(
            [
                "--check",
                "--if-present",
                "--aosh-root",
                str(missing),
            ]
        )
        == 0
    )
    assert "skip: AOSH checkout is absent" in capsys.readouterr().out


def test_present_incomplete_checkout_fails_closed(
    board_sources: tuple[Path, Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    aosh_root, roles_path, ward_roles_path = board_sources
    (aosh_root / harness_board_sync.SELECTIONS_PATH).unlink()

    assert (
        harness_board_sync.main(
            [
                "--check",
                "--if-present",
                "--aosh-root",
                str(aosh_root),
                "--roles",
                str(roles_path),
                "--ward-roles",
                str(ward_roles_path),
            ]
        )
        == 2
    )
    assert "harness-board-sync: read" in capsys.readouterr().err


@pytest.mark.parametrize("failure", ["missing-lane", "rationale", "incompatible"])
def test_malformed_selections_fail_closed(
    board_sources: tuple[Path, Path, Path], failure: str
) -> None:
    aosh_root, roles_path, _ = board_sources
    selections_path = aosh_root / harness_board_sync.SELECTIONS_PATH

    def mutate(document: dict[str, object]) -> None:
        selections = document["selections"]
        assert isinstance(selections, dict)
        engineer = selections["engineer"]
        assert isinstance(engineer, dict)
        if failure == "missing-lane":
            del engineer["autonomous-coding"]
        elif failure == "rationale":
            selection = engineer["autonomous-coding"]
            assert isinstance(selection, dict)
            selection["rationale"] = "not part of the contract"
        else:
            engineer["autonomous-coding"] = {"agent": "aider"}

    _rewrite_yaml(selections_path, mutate)

    with pytest.raises(harness_board_sync.BoardSyncError):
        harness_board_sync.load_board(aosh_root, roles_path=roles_path)


def test_unattended_intent_belongs_only_to_engineer(
    board_sources: tuple[Path, Path, Path],
) -> None:
    aosh_root, roles_path, _ = board_sources

    def mutate_roles(document: dict[str, object]) -> None:
        roles = document["roles"]
        assert isinstance(roles, dict)
        advisor = roles["advisor"]
        assert isinstance(advisor, dict)
        advisor["intents"] = ["autonomous-coding"]

    def mutate_selections(document: dict[str, object]) -> None:
        selections = document["selections"]
        assert isinstance(selections, dict)
        selections["advisor"] = {"autonomous-coding": {"agent": "openhands"}}

    _rewrite_yaml(aosh_root / harness_board_sync.ROLES_PATH, mutate_roles)
    _rewrite_yaml(aosh_root / harness_board_sync.SELECTIONS_PATH, mutate_selections)

    with pytest.raises(harness_board_sync.BoardSyncError, match="exclusively"):
        harness_board_sync.load_board(aosh_root, roles_path=roles_path)


def test_merge_ward_board_rejects_malformed_generated_markers(
    board_sources: tuple[Path, Path, Path],
) -> None:
    aosh_root, roles_path, ward_roles_path = board_sources
    board = harness_board_sync.load_board(aosh_root, roles_path=roles_path)

    with pytest.raises(harness_board_sync.BoardSyncError, match="marker pair"):
        harness_board_sync.merge_ward_board(
            ward_roles_path.read_text(encoding="utf-8")
            + f"\n{harness_board_sync.KDL_BEGIN}\n",
            harness_board_sync.render_ward_board(board),
            ward_roles_path,
        )

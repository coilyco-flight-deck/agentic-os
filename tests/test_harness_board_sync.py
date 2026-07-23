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
def board_sources(tmp_path: Path) -> tuple[Path, Path]:
    aosh_root = tmp_path / "aosh"
    shutil.copytree(FIXTURE_ROOT, aosh_root)
    return aosh_root, aosh_root / "roles.kdl"


def _rewrite_yaml(path: Path, mutate: Callable[[dict[str, object]], None]) -> None:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    mutate(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_fixture_renders_deterministic_model_opaque_projection(
    board_sources: tuple[Path, Path],
) -> None:
    aosh_root, roles_path = board_sources

    board = harness_board_sync.load_board(aosh_root, roles_path=roles_path)
    rendered = harness_board_sync.render_board(board)

    assert rendered == (aosh_root / "expected.json").read_text(encoding="utf-8")
    payload = json.loads(rendered)
    director = next(route for route in payload["roles"] if route["role"] == "director")
    customer_success = next(
        route for route in payload["roles"] if route["role"] == "customer-success"
    )
    assert director["intents"][0]["harness"] == "plandex"
    assert [lane["harness"] for lane in customer_success["intents"]] == [
        "rasa",
        "rasa",
    ]
    assert not {"model", "server", "fallback", "orchestrator", "rationale"} & set(
        rendered.split('"')
    )


def test_check_reports_drift_without_writing(
    board_sources: tuple[Path, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    aosh_root, roles_path = board_sources
    output = tmp_path / "role-harnesses.json"
    output.write_text("{}\n", encoding="utf-8")

    assert (
        harness_board_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
            check=True,
        )
        == 1
    )
    assert output.read_text(encoding="utf-8") == "{}\n"
    assert "drift:" in capsys.readouterr().err


def test_sync_writes_then_check_passes(
    board_sources: tuple[Path, Path], tmp_path: Path
) -> None:
    aosh_root, roles_path = board_sources
    output = tmp_path / "role-harnesses.json"

    assert (
        harness_board_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
            check=False,
        )
        == 0
    )
    assert (
        harness_board_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
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
    board_sources: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    aosh_root, roles_path = board_sources
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
            ]
        )
        == 2
    )
    assert "harness-board-sync: read" in capsys.readouterr().err


@pytest.mark.parametrize("failure", ["missing-lane", "rationale", "incompatible"])
def test_malformed_selections_fail_closed(
    board_sources: tuple[Path, Path], failure: str
) -> None:
    aosh_root, roles_path = board_sources
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
    board_sources: tuple[Path, Path],
) -> None:
    aosh_root, roles_path = board_sources

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

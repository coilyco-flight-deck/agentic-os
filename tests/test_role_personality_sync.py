from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agentic_os import role_personality_sync


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "harness_board"


@pytest.fixture
def personality_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    aosh_root = tmp_path / "aosh"
    shutil.copytree(FIXTURE_ROOT, aosh_root)
    roles_path = aosh_root / "roles.kdl"
    return aosh_root, roles_path, tmp_path / "projection.json"


def test_projection_round_trips_ordered_role_personalities(
    personality_sources: tuple[Path, Path, Path],
) -> None:
    aosh_root, roles_path, output = personality_sources
    orientation = role_personality_sync.load_orientation(
        aosh_root,
        roles_path=roles_path,
    )

    output.write_text(
        role_personality_sync.render_projection(orientation),
        encoding="utf-8",
    )
    projected = role_personality_sync.load_projection(output)

    assert projected == {
        role.role: role.personalities for role in orientation.roles
    }


def test_sync_writes_then_check_passes(
    personality_sources: tuple[Path, Path, Path],
) -> None:
    aosh_root, roles_path, output = personality_sources

    assert (
        role_personality_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
            check=False,
        )
        == 0
    )
    assert (
        role_personality_sync.run(
            aosh_root,
            output,
            roles_path=roles_path,
            check=True,
        )
        == 0
    )


def test_projection_rejects_missing_personality_binding(
    personality_sources: tuple[Path, Path, Path],
) -> None:
    aosh_root, roles_path, output = personality_sources
    orientation = role_personality_sync.load_orientation(
        aosh_root,
        roles_path=roles_path,
    )
    document = json.loads(
        role_personality_sync.render_projection(orientation)
    )
    document["skills"].pop()
    output.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(
        role_personality_sync.RolePersonalitySyncError,
        match="bindings do not match",
    ):
        role_personality_sync.load_projection(output)


def test_if_present_skips_only_an_absent_checkout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing-aosh"

    assert (
        role_personality_sync.main(
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

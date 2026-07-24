from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_os import role_personality_sync


def _person_snapshot() -> dict[str, object]:
    return {
        "format": role_personality_sync.PERSON_SNAPSHOT_FORMAT,
        "schema_version": role_personality_sync.PERSON_SNAPSHOT_SCHEMA_VERSION,
        "source": "person:fixture",
        "person": "fixture",
        "role_order": ["builder", "guide"],
        "roles": {
            "builder": {
                "personalities": ["curious", "grounded"],
            },
            "guide": {
                "personalities": ["playful", "diplomatic"],
            },
        },
        "personalities": {
            personality: {
                "skill": role_personality_sync.personality_skill_id(personality)
            }
            for personality in ("curious", "grounded", "playful", "diplomatic")
        },
    }


@pytest.fixture
def personality_sources(tmp_path: Path) -> tuple[Path, Path]:
    snapshot = tmp_path / "person.json"
    snapshot.write_text(
        json.dumps(_person_snapshot(), indent=2) + "\n",
        encoding="utf-8",
    )
    return snapshot, tmp_path / "projection.json"


def test_projection_round_trips_ordered_role_personalities(
    personality_sources: tuple[Path, Path],
) -> None:
    snapshot_path, output = personality_sources
    snapshot = role_personality_sync.load_person_snapshot(snapshot_path)

    output.write_text(
        role_personality_sync.render_projection(snapshot),
        encoding="utf-8",
    )
    projected = role_personality_sync.load_projection(output)

    assert projected == {
        role.role: role.personalities for role in snapshot.roles
    }


def test_sync_writes_then_check_passes(
    personality_sources: tuple[Path, Path],
) -> None:
    snapshot, output = personality_sources

    assert role_personality_sync.run(snapshot, output, check=False) == 0
    assert role_personality_sync.run(snapshot, output, check=True) == 0


def test_snapshot_rejects_invalid_personality_binding(
    personality_sources: tuple[Path, Path],
) -> None:
    snapshot, _ = personality_sources
    document = json.loads(snapshot.read_text(encoding="utf-8"))
    document["personalities"]["playful"]["skill"] = "personality-wrong"
    snapshot.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(
        role_personality_sync.RolePersonalitySyncError,
        match="invalid skill binding",
    ):
        role_personality_sync.load_person_snapshot(snapshot)


def test_projection_rejects_missing_personality_binding(
    personality_sources: tuple[Path, Path],
) -> None:
    snapshot_path, output = personality_sources
    snapshot = role_personality_sync.load_person_snapshot(snapshot_path)
    document = json.loads(
        role_personality_sync.render_projection(snapshot)
    )
    document["skills"].pop()
    output.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(
        role_personality_sync.RolePersonalitySyncError,
        match="bindings do not match",
    ):
        role_personality_sync.load_projection(output)


def test_if_present_skips_only_an_absent_snapshot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing-person.json"

    assert (
        role_personality_sync.main(
            [
                "--check",
                "--if-present",
                "--person-snapshot",
                str(missing),
            ]
        )
        == 0
    )
    assert (
        "skip: agent-compose person snapshot is absent"
        in capsys.readouterr().out
    )

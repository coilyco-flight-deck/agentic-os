"""Tests for agentic_os.agent_compose: the opt-in composer spine (forgejo #135)."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os import agent_compose


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "config": tmp_path / "agent-compose.yaml",
        "composed": tmp_path / "composed.md",
        "claude": tmp_path / "harness" / "claude" / "CLAUDE.md",
        "codex": tmp_path / "harness" / "codex" / "AGENTS.md",
        "tmp": tmp_path,
    }


# ---------- opt-in: no config is a total no-op ----------

def test_no_config_is_noop(paths: dict[str, Path]) -> None:
    rc = agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0
    assert not paths["composed"].exists()


# ---------- happy path ----------

def test_composes_and_symlinks(paths: dict[str, Path], tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\nbe excellent\n")
    write(
        paths["config"],
        f"sources:\n  - {src}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )

    rc = agent_compose.run(paths["config"], paths["composed"])

    assert rc == 0
    body = paths["composed"].read_text(encoding="utf-8")
    assert "be excellent" in body
    assert body.startswith(agent_compose.BANNER)
    for dst in (paths["claude"], paths["codex"]):
        assert dst.is_symlink()
        assert dst.resolve() == paths["composed"].resolve()
        assert dst.read_text(encoding="utf-8") == body


def test_compose_is_deterministic(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "stable content\n")
    assert agent_compose.compose([src]) == agent_compose.compose([src])


# ---------- missing source is an error, not a silent skip ----------

def test_missing_source_fails(paths: dict[str, Path], tmp_path: Path) -> None:
    write(paths["config"], f"sources:\n  - {tmp_path / 'nope.md'}\n")
    rc = agent_compose.run(paths["config"], paths["composed"])
    assert rc == 1
    assert not paths["composed"].exists()


# ---------- dry-run touches nothing ----------

def test_dry_run_writes_nothing(paths: dict[str, Path], tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "x\n")
    write(paths["config"], f"sources:\n  - {src}\n")
    rc = agent_compose.run(paths["config"], paths["composed"], dry_run=True)
    assert rc == 0
    assert not paths["composed"].exists()


# ---------- symlink backs up a pre-existing real file ----------

def test_install_symlink_backs_up_real_file(tmp_path: Path) -> None:
    target = tmp_path / "composed.md"
    target.write_text("composed", encoding="utf-8")
    dst = tmp_path / "CLAUDE.md"
    dst.write_text("old real file", encoding="utf-8")

    agent_compose.install_symlink(dst, target)

    assert dst.is_symlink()
    backup = dst.with_name("CLAUDE.md.bak")
    assert backup.read_text(encoding="utf-8") == "old real file"


def test_install_symlink_replaces_existing_symlink(tmp_path: Path) -> None:
    target = tmp_path / "composed.md"
    target.write_text("new", encoding="utf-8")
    old_target = tmp_path / "old.md"
    old_target.write_text("old", encoding="utf-8")
    dst = tmp_path / "CLAUDE.md"
    dst.symlink_to(old_target)

    agent_compose.install_symlink(dst, target)

    assert dst.resolve() == target.resolve()
    assert not dst.with_name("CLAUDE.md.bak").exists()


# ---------- load-point resolution: defaults + opt-in openclaw ----------

def test_openclaw_skipped_when_unset() -> None:
    points = agent_compose.resolve_load_points({})
    assert set(points) == {"claude", "codex"}


def test_openclaw_included_when_set(tmp_path: Path) -> None:
    claw = tmp_path / "openclaw" / "AGENTS.md"
    points = agent_compose.resolve_load_points({"load_points": {"openclaw": str(claw)}})
    assert points["openclaw"] == claw


def test_load_point_override(tmp_path: Path) -> None:
    custom = tmp_path / "custom-claude.md"
    points = agent_compose.resolve_load_points({"load_points": {"claude": str(custom)}})
    assert points["claude"] == custom

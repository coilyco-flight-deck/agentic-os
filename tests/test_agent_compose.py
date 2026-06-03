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


# ---------- source discovery via roots (forgejo #136) ----------

def test_discover_finds_source_files(tmp_path: Path) -> None:
    write(tmp_path / "repoA" / "AGENTS.COMPOSE.md", "a\n")
    write(tmp_path / "repoB" / "nested" / "AGENTS.COMPOSE.md", "b\n")
    write(tmp_path / "repoA" / "AGENTS.md", "not a source\n")
    found = agent_compose.discover_sources(tmp_path)
    names = [p.name for p in found]
    assert names == ["AGENTS.COMPOSE.md", "AGENTS.COMPOSE.md"]
    assert all(p.name == "AGENTS.COMPOSE.md" for p in found)


def test_discover_is_sorted(tmp_path: Path) -> None:
    write(tmp_path / "z" / "AGENTS.COMPOSE.md", "z\n")
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", "a\n")
    found = agent_compose.discover_sources(tmp_path)
    assert found == sorted(found, key=str)


def test_discover_skips_dot_dirs(tmp_path: Path) -> None:
    write(tmp_path / ".git" / "AGENTS.COMPOSE.md", "vcs noise\n")
    write(tmp_path / "real" / "AGENTS.COMPOSE.md", "real\n")
    found = agent_compose.discover_sources(tmp_path)
    assert len(found) == 1
    assert "real" in str(found[0])


def test_discover_none_found(tmp_path: Path) -> None:
    write(tmp_path / "repo" / "AGENTS.md", "no compose file here\n")
    assert agent_compose.discover_sources(tmp_path) == []


def test_gather_explicit_then_discovered(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.md"
    write(explicit, "explicit\n")
    write(tmp_path / "root" / "AGENTS.COMPOSE.md", "discovered\n")
    config = {"sources": [str(explicit)], "roots": [str(tmp_path / "root")]}
    sources, errors = agent_compose.gather_sources(config)
    assert errors == []
    assert sources[0] == explicit
    assert sources[1].name == "AGENTS.COMPOSE.md"


def test_gather_multiple_roots(tmp_path: Path) -> None:
    write(tmp_path / "r1" / "AGENTS.COMPOSE.md", "1\n")
    write(tmp_path / "r2" / "AGENTS.COMPOSE.md", "2\n")
    config = {"roots": [str(tmp_path / "r1"), str(tmp_path / "r2")]}
    sources, errors = agent_compose.gather_sources(config)
    assert errors == []
    assert len(sources) == 2


def test_gather_dedups_listed_and_discovered(tmp_path: Path) -> None:
    src = tmp_path / "root" / "AGENTS.COMPOSE.md"
    write(src, "once\n")
    config = {"sources": [str(src)], "roots": [str(tmp_path / "root")]}
    sources, errors = agent_compose.gather_sources(config)
    assert errors == []
    assert len(sources) == 1


def test_gather_missing_root_is_error(tmp_path: Path) -> None:
    config = {"roots": [str(tmp_path / "nonexistent")]}
    sources, errors = agent_compose.gather_sources(config)
    assert sources == []
    assert len(errors) == 1 and "not a directory" in errors[0]


def test_run_discovers_through_roots(paths: dict[str, Path], tmp_path: Path) -> None:
    write(tmp_path / "root" / "AGENTS.COMPOSE.md", "discovered doctrine\n")
    write(
        paths["config"],
        f"roots:\n  - {tmp_path / 'root'}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    rc = agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0
    assert "discovered doctrine" in paths["composed"].read_text(encoding="utf-8")


def test_run_empty_sources_refuses(paths: dict[str, Path], tmp_path: Path) -> None:
    write(tmp_path / "root" / "AGENTS.md", "not a source\n")
    write(paths["config"], f"roots:\n  - {tmp_path / 'root'}\n")
    rc = agent_compose.run(paths["config"], paths["composed"])
    assert rc == 1
    assert not paths["composed"].exists()

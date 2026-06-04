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


def test_codex_disabled_via_null(tmp_path: Path) -> None:
    points = agent_compose.resolve_load_points(
        {"load_points": {"claude": str(tmp_path / "c.md"), "codex": None}}
    )
    assert set(points) == {"claude"}


def test_claude_disabled_via_false(tmp_path: Path) -> None:
    points = agent_compose.resolve_load_points(
        {"load_points": {"claude": False, "codex": str(tmp_path / "x.md")}}
    )
    assert set(points) == {"codex"}


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


# ---------- frontmatter + scopes (forgejo #137) ----------

def test_parse_source_reads_scopes(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "---\nscopes: [a, b]\n---\nbody text\n")
    scopes, body = agent_compose.parse_source(src)
    assert scopes == ["a", "b"]
    assert body.strip() == "body text"


def test_parse_source_single_scope_string(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "---\nscopes: kai-public\n---\nx\n")
    assert agent_compose.parse_source(src)[0] == ["kai-public"]


def test_parse_source_no_frontmatter(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "# just doctrine\nno frontmatter\n")
    scopes, body = agent_compose.parse_source(src)
    assert scopes is None
    assert "just doctrine" in body


def test_compose_strips_frontmatter(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "---\nscopes: [kai-public]\n---\n# doctrine\nrule one\n")
    out = agent_compose.compose([src])
    assert "scopes:" not in out
    assert "# doctrine" in out and "rule one" in out


def test_select_no_machine_scopes_keeps_all(tmp_path: Path) -> None:
    a = tmp_path / "a" / "AGENTS.COMPOSE.md"
    b = tmp_path / "b" / "AGENTS.COMPOSE.md"
    write(a, "x\n")
    write(b, "y\n")
    assert agent_compose.select_by_scope([a, b], None) == [a, b]


def test_select_drops_untagged_under_filtering(tmp_path: Path) -> None:
    tagged = tmp_path / "t" / "AGENTS.COMPOSE.md"
    untagged = tmp_path / "u" / "AGENTS.COMPOSE.md"
    write(tagged, "---\nscopes: [eco]\n---\nx\n")
    write(untagged, "plain\n")
    assert agent_compose.select_by_scope([tagged, untagged], ["eco"]) == [tagged]


# The canonical compat matrix from forgejo #134's compat-matrix comment.
SCOPE_SOURCES = ["kai-public", "work", "kai-private", "eco"]
MATRIX = {
    "work-mac": (["work", "kai-public"], {"work", "kai-public"}),
    "personal-mac": (["kai-public", "kai-private"], {"kai-public", "kai-private"}),
    "personal-windows": (["kai-public", "eco"], {"kai-public", "eco"}),
}


def _build_scoped_sources(tmp_path: Path) -> list[Path]:
    out = []
    for name in SCOPE_SOURCES:
        p = tmp_path / name / "AGENTS.COMPOSE.md"
        write(p, f"---\nscopes: [{name}]\n---\n# {name} doctrine\n")
        out.append(p)
    return out


@pytest.mark.parametrize("machine", list(MATRIX))
def test_compat_matrix(machine: str, tmp_path: Path) -> None:
    sources = _build_scoped_sources(tmp_path)
    machine_scopes, expected = MATRIX[machine]
    selected = agent_compose.select_by_scope(sources, machine_scopes)
    assert {p.parent.name for p in selected} == expected


def test_run_filters_by_scope(paths: dict[str, Path], tmp_path: Path) -> None:
    pub = tmp_path / "pub" / "AGENTS.COMPOSE.md"
    eco = tmp_path / "eco" / "AGENTS.COMPOSE.md"
    write(pub, "---\nscopes: [kai-public]\n---\npublic rule\n")
    write(eco, "---\nscopes: [eco]\n---\neco rule\n")
    write(
        paths["config"],
        f"scopes: [kai-public]\nsources:\n  - {pub}\n  - {eco}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    rc = agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0
    out = paths["composed"].read_text(encoding="utf-8")
    assert "public rule" in out and "eco rule" not in out


def test_run_no_scope_match_refuses(paths: dict[str, Path], tmp_path: Path) -> None:
    eco = tmp_path / "eco" / "AGENTS.COMPOSE.md"
    write(eco, "---\nscopes: [eco]\n---\neco\n")
    write(paths["config"], f"scopes: [work]\nsources:\n  - {eco}\n")
    rc = agent_compose.run(paths["config"], paths["composed"])
    assert rc == 1
    assert not paths["composed"].exists()


# ---------- drift detection (forgejo #140) ----------

def _written_config(paths: dict[str, Path], tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "stable doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {src}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )


def test_check_no_config_is_noop(paths: dict[str, Path]) -> None:
    assert agent_compose.check(paths["config"], paths["composed"]) == 0


def test_check_in_sync(paths: dict[str, Path], tmp_path: Path) -> None:
    _written_config(paths, tmp_path)
    agent_compose.run(paths["config"], paths["composed"])
    assert agent_compose.check(paths["config"], paths["composed"]) == 0


def test_check_detects_handedit(paths: dict[str, Path], tmp_path: Path) -> None:
    _written_config(paths, tmp_path)
    agent_compose.run(paths["config"], paths["composed"])
    paths["composed"].write_text("hand-edited junk\n", encoding="utf-8")
    assert agent_compose.check(paths["config"], paths["composed"]) == 1


def test_check_detects_missing_output(paths: dict[str, Path], tmp_path: Path) -> None:
    _written_config(paths, tmp_path)
    assert agent_compose.check(paths["config"], paths["composed"]) == 1

"""Tests for agentic_os.generators.generate_agent_compose: the opt-in composer spine (forgejo #135)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_os.generators import generate_agent_compose


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_default_load_points(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stop tests from re-pointing the real ~/.claude and ~/.codex symlinks.

    A test that omits `load_points` falls through to DEFAULT_LOAD_POINTS, which
    is the operator's real load points. Without this, run() would clobber them
    (and leave them dangling at a deleted tmp file). Redirect the defaults into
    a throwaway dir for every test.
    """
    safe = tmp_path_factory.mktemp("load-points")
    monkeypatch.setattr(
        generate_agent_compose,
        "DEFAULT_LOAD_POINTS",
        {
            "claude": safe / "claude" / "CLAUDE.md",
            "codex": safe / "codex" / "AGENTS.md",
        },
    )


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
    rc = generate_agent_compose.run(paths["config"], paths["composed"])
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

    rc = generate_agent_compose.run(paths["config"], paths["composed"])

    assert rc == 0
    body = paths["composed"].read_text(encoding="utf-8")
    assert "be excellent" in body
    assert body.startswith(generate_agent_compose.BANNER)
    for dst in (paths["claude"], paths["codex"]):
        assert dst.is_symlink()
        assert dst.resolve() == paths["composed"].resolve()
        assert dst.read_text(encoding="utf-8") == body


def test_compose_is_deterministic(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "stable content\n")
    assert generate_agent_compose.compose([src]) == generate_agent_compose.compose(
        [src]
    )


# ---------- a missing source degrades (warn + skip), it does not freeze ----------


def test_missing_source_degrades_when_others_survive(
    paths: dict[str, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One missing source must not freeze the whole load point.

    A wrong host-class entry (e.g. a work overlay listed on a personal mac) once
    aborted the entire compose, silently freezing COMPOSED.md for every harness.
    Now the present sources still compose and the missing one is a loud warning.
    """
    ok = tmp_path / "AGENTS.COMPOSE.md"
    write(ok, "# present\nstill here\n")
    write(paths["config"], f"sources:\n  - {tmp_path / 'nope.md'}\n  - {ok}\n")
    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0
    assert "still here" in paths["composed"].read_text(encoding="utf-8")
    assert "nope.md" in capsys.readouterr().err  # surfaced, not swallowed


def test_all_sources_missing_still_refuses(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    """With nothing left to compose, the empty-output guard still fires."""
    write(paths["config"], f"sources:\n  - {tmp_path / 'nope.md'}\n")
    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 1
    assert not paths["composed"].exists()


# ---------- a no-op recompose is silent and does not churn the file ----------


def test_unchanged_recompose_is_silent(
    paths: dict[str, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The freshen hook runs run() every session; a no-op must stay quiet.

    No "wrote" line (so hook stdout is empty when nothing changed) and no rewrite
    of unchanged content (so mtime does not churn each session).
    """
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\nstable\n")
    write(paths["config"], f"sources:\n  - {src}\n")

    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0
    capsys.readouterr()  # drain the first-write output
    before = paths["composed"].stat().st_mtime_ns

    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0
    assert "wrote" not in capsys.readouterr().out
    assert paths["composed"].stat().st_mtime_ns == before


# ---------- dry-run touches nothing ----------


def test_dry_run_writes_nothing(paths: dict[str, Path], tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "x\n")
    write(paths["config"], f"sources:\n  - {src}\n")
    rc = generate_agent_compose.run(paths["config"], paths["composed"], dry_run=True)
    assert rc == 0
    assert not paths["composed"].exists()


# ---------- symlink backs up a pre-existing real file ----------


def test_install_symlink_backs_up_real_file(tmp_path: Path) -> None:
    target = tmp_path / "composed.md"
    target.write_text("composed", encoding="utf-8")
    dst = tmp_path / "CLAUDE.md"
    dst.write_text("old real file", encoding="utf-8")

    generate_agent_compose.install_symlink(dst, target)

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

    line = generate_agent_compose.install_symlink(dst, target)

    assert line is not None  # a real relink reports
    assert dst.resolve() == target.resolve()
    assert not dst.with_name("CLAUDE.md.bak").exists()


def test_install_symlink_noop_is_silent(tmp_path: Path) -> None:
    """An already-correct link returns None so the freshen hook stays quiet."""
    target = tmp_path / "composed.md"
    target.write_text("x", encoding="utf-8")
    dst = tmp_path / "CLAUDE.md"
    dst.symlink_to(target)

    assert generate_agent_compose.install_symlink(dst, target) is None
    assert dst.readlink() == target  # left intact


# ---------- load-point resolution: defaults + opt-in opencode ----------


def test_opencode_skipped_when_unset() -> None:
    points = generate_agent_compose.resolve_load_points({})
    assert set(points) == {"claude", "codex"}


def test_opencode_included_when_set(tmp_path: Path) -> None:
    oc = tmp_path / "opencode" / "AGENTS.md"
    points = generate_agent_compose.resolve_load_points(
        {"load_points": {"opencode": str(oc)}}
    )
    assert points["opencode"] == oc


def test_load_point_override(tmp_path: Path) -> None:
    custom = tmp_path / "custom-claude.md"
    points = generate_agent_compose.resolve_load_points(
        {"load_points": {"claude": str(custom)}}
    )
    assert points["claude"] == custom


def test_codex_disabled_via_null(tmp_path: Path) -> None:
    points = generate_agent_compose.resolve_load_points(
        {"load_points": {"claude": str(tmp_path / "c.md"), "codex": None}}
    )
    assert set(points) == {"claude"}


def test_claude_disabled_via_false(tmp_path: Path) -> None:
    points = generate_agent_compose.resolve_load_points(
        {"load_points": {"claude": False, "codex": str(tmp_path / "x.md")}}
    )
    assert set(points) == {"codex"}


# ---------- source discovery via roots (forgejo #136) ----------


def test_discover_finds_source_files(tmp_path: Path) -> None:
    write(tmp_path / "repoA" / "AGENTS.COMPOSE.md", "a\n")
    write(tmp_path / "repoB" / "nested" / "AGENTS.COMPOSE.md", "b\n")
    write(tmp_path / "repoA" / "AGENTS.md", "not a source\n")
    found = generate_agent_compose.discover_sources(tmp_path)
    names = [p.name for p in found]
    assert names == ["AGENTS.COMPOSE.md", "AGENTS.COMPOSE.md"]
    assert all(p.name == "AGENTS.COMPOSE.md" for p in found)


def test_discover_is_sorted(tmp_path: Path) -> None:
    write(tmp_path / "z" / "AGENTS.COMPOSE.md", "z\n")
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", "a\n")
    found = generate_agent_compose.discover_sources(tmp_path)
    assert found == sorted(found, key=str)


def test_discover_skips_dot_dirs(tmp_path: Path) -> None:
    write(tmp_path / ".git" / "AGENTS.COMPOSE.md", "vcs noise\n")
    write(tmp_path / "real" / "AGENTS.COMPOSE.md", "real\n")
    found = generate_agent_compose.discover_sources(tmp_path)
    assert len(found) == 1
    assert "real" in str(found[0])


def test_discover_none_found(tmp_path: Path) -> None:
    write(tmp_path / "repo" / "AGENTS.md", "no compose file here\n")
    assert generate_agent_compose.discover_sources(tmp_path) == []


def test_gather_explicit_then_discovered(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.md"
    write(explicit, "explicit\n")
    write(tmp_path / "root" / "AGENTS.COMPOSE.md", "discovered\n")
    config = {"sources": [str(explicit)], "roots": [str(tmp_path / "root")]}
    sources, errors = generate_agent_compose.gather_sources(config)
    assert errors == []
    assert sources[0] == explicit
    assert sources[1].name == "AGENTS.COMPOSE.md"


def test_gather_multiple_roots(tmp_path: Path) -> None:
    write(tmp_path / "r1" / "AGENTS.COMPOSE.md", "1\n")
    write(tmp_path / "r2" / "AGENTS.COMPOSE.md", "2\n")
    config = {"roots": [str(tmp_path / "r1"), str(tmp_path / "r2")]}
    sources, errors = generate_agent_compose.gather_sources(config)
    assert errors == []
    assert len(sources) == 2


def test_gather_dedups_listed_and_discovered(tmp_path: Path) -> None:
    src = tmp_path / "root" / "AGENTS.COMPOSE.md"
    write(src, "once\n")
    config = {"sources": [str(src)], "roots": [str(tmp_path / "root")]}
    sources, errors = generate_agent_compose.gather_sources(config)
    assert errors == []
    assert len(sources) == 1


def test_gather_missing_root_is_error(tmp_path: Path) -> None:
    config = {"roots": [str(tmp_path / "nonexistent")]}
    sources, errors = generate_agent_compose.gather_sources(config)
    assert sources == []
    assert len(errors) == 1 and "not a directory" in errors[0]


def test_run_discovers_through_roots(paths: dict[str, Path], tmp_path: Path) -> None:
    write(tmp_path / "root" / "AGENTS.COMPOSE.md", "discovered doctrine\n")
    write(
        paths["config"],
        f"roots:\n  - {tmp_path / 'root'}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0
    assert "discovered doctrine" in paths["composed"].read_text(encoding="utf-8")


def test_run_empty_sources_refuses(paths: dict[str, Path], tmp_path: Path) -> None:
    write(tmp_path / "root" / "AGENTS.md", "not a source\n")
    write(paths["config"], f"roots:\n  - {tmp_path / 'root'}\n")
    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 1
    assert not paths["composed"].exists()


# ---------- frontmatter + scopes (forgejo #137) ----------


def test_parse_source_reads_scopes(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "---\nscopes: [a, b]\n---\nbody text\n")
    scopes, body = generate_agent_compose.parse_source(src)
    assert scopes == ["a", "b"]
    assert body.strip() == "body text"


def test_parse_source_single_scope_string(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "---\nscopes: kai-public\n---\nx\n")
    assert generate_agent_compose.parse_source(src)[0] == ["kai-public"]


def test_parse_source_no_frontmatter(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "# just doctrine\nno frontmatter\n")
    scopes, body = generate_agent_compose.parse_source(src)
    assert scopes is None
    assert "just doctrine" in body


def test_compose_strips_frontmatter(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(
        src,
        "---\nscopes: [kai-public]\nharnesses: [claude]\n---\n"
        "# doctrine\nrule one\n",
    )
    out = generate_agent_compose.compose([src])
    assert "scopes:" not in out
    assert "harnesses:" not in out
    assert "# doctrine" in out and "rule one" in out


def test_select_no_machine_scopes_keeps_all(tmp_path: Path) -> None:
    a = tmp_path / "a" / "AGENTS.COMPOSE.md"
    b = tmp_path / "b" / "AGENTS.COMPOSE.md"
    write(a, "x\n")
    write(b, "y\n")
    assert generate_agent_compose.select_by_scope([a, b], None) == [a, b]


def test_select_drops_untagged_under_filtering(tmp_path: Path) -> None:
    tagged = tmp_path / "t" / "AGENTS.COMPOSE.md"
    untagged = tmp_path / "u" / "AGENTS.COMPOSE.md"
    write(tagged, "---\nscopes: [eco]\n---\nx\n")
    write(untagged, "plain\n")
    assert generate_agent_compose.select_by_scope([tagged, untagged], ["eco"]) == [
        tagged
    ]


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
    selected = generate_agent_compose.select_by_scope(sources, machine_scopes)
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
    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0
    out = paths["composed"].read_text(encoding="utf-8")
    assert "public rule" in out and "eco rule" not in out


def test_run_no_scope_match_refuses(paths: dict[str, Path], tmp_path: Path) -> None:
    eco = tmp_path / "eco" / "AGENTS.COMPOSE.md"
    write(eco, "---\nscopes: [eco]\n---\neco\n")
    write(paths["config"], f"scopes: [work]\nsources:\n  - {eco}\n")
    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 1
    assert not paths["composed"].exists()


# ---------- harness slices ----------


def test_source_harnesses_reads_allowlist(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "---\nharnesses: [claude, codex]\n---\nx\n")
    assert generate_agent_compose.source_harnesses(src) == ["claude", "codex"]


def test_source_without_harnesses_is_shared(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "shared\n")
    assert generate_agent_compose.select_by_harness([src], "codex") == [src]


def test_run_writes_divergent_harness_slices(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    shared = tmp_path / "shared.md"
    claude_only = tmp_path / "claude.md"
    write(shared, "shared doctrine\n")
    write(claude_only, "---\nharnesses: [claude]\n---\nclaude doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {shared}\n  - {claude_only}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )

    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0

    claude_output = tmp_path / "composed.claude.md"
    codex_output = tmp_path / "composed.codex.md"
    assert paths["claude"].resolve() == claude_output.resolve()
    assert paths["codex"].resolve() == codex_output.resolve()
    assert "claude doctrine" in claude_output.read_text(encoding="utf-8")
    assert "claude doctrine" not in codex_output.read_text(encoding="utf-8")
    assert "shared doctrine" in codex_output.read_text(encoding="utf-8")
    assert not paths["composed"].exists()


def test_run_refuses_empty_harness_slice(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    claude_only = tmp_path / "claude.md"
    write(claude_only, "---\nharnesses: [claude]\n---\nclaude doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {claude_only}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 1
    assert not paths["claude"].exists()
    assert not paths["codex"].exists()


def test_run_removes_obsolete_shared_output(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    shared = tmp_path / "shared.md"
    claude_only = tmp_path / "claude.md"
    write(shared, "shared doctrine\n")
    write(paths["config"], f"sources:\n  - {shared}\n")
    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0
    assert paths["composed"].exists()

    write(claude_only, "---\nharnesses: [claude]\n---\nclaude doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {shared}\n  - {claude_only}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0
    assert not paths["composed"].exists()


def test_run_preserves_similarly_named_user_file(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    src = tmp_path / "shared.md"
    user_file = tmp_path / "composed.notes.md"
    write(src, "shared doctrine\n")
    write(user_file, "user-owned notes\n")
    write(paths["config"], f"sources:\n  - {src}\n")
    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0
    assert user_file.read_text(encoding="utf-8") == "user-owned notes\n"


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
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 0


def test_check_in_sync(paths: dict[str, Path], tmp_path: Path) -> None:
    _written_config(paths, tmp_path)
    generate_agent_compose.run(paths["config"], paths["composed"])
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 0


def test_check_detects_handedit(paths: dict[str, Path], tmp_path: Path) -> None:
    _written_config(paths, tmp_path)
    generate_agent_compose.run(paths["config"], paths["composed"])
    paths["composed"].write_text("hand-edited junk\n", encoding="utf-8")
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 1


def test_check_detects_missing_output(paths: dict[str, Path], tmp_path: Path) -> None:
    _written_config(paths, tmp_path)
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 1


def test_check_detects_drift_in_one_harness_slice(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    shared = tmp_path / "shared.md"
    claude_only = tmp_path / "claude.md"
    write(shared, "shared doctrine\n")
    write(claude_only, "---\nharnesses: [claude]\n---\nclaude doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {shared}\n  - {claude_only}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    generate_agent_compose.run(paths["config"], paths["composed"])
    (tmp_path / "composed.codex.md").write_text("drift\n", encoding="utf-8")
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 1


def test_check_detects_obsolete_generated_output(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    shared = tmp_path / "shared.md"
    claude_only = tmp_path / "claude.md"
    write(shared, "shared doctrine\n")
    write(claude_only, "---\nharnesses: [claude]\n---\nclaude doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {shared}\n  - {claude_only}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    generate_agent_compose.run(paths["config"], paths["composed"])
    write(paths["composed"], generate_agent_compose.compose([shared]))
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 1


# ---------- per-harness section overrides ----------


def test_apply_overrides_replaces_matching_section() -> None:
    base = "## Keep\nkeep me\n\n## Reading\nread the whole file\n"
    override = "## Reading\nread slices only\n"
    out = generate_agent_compose.apply_overrides(base, override)
    assert "read slices only" in out
    assert "read the whole file" not in out
    assert "keep me" in out  # untouched section survives


def test_apply_overrides_appends_new_section() -> None:
    base = "## Keep\nkeep me\n"
    override = "## Reading\nread slices only\n"
    out = generate_agent_compose.apply_overrides(base, override)
    assert "keep me" in out
    assert out.strip().endswith("read slices only")


def test_apply_overrides_section_absorbs_subsections() -> None:
    base = "## Rules\nintro\n### Sub\nold sub\n\n## After\ntail\n"
    override = "## Rules\nfresh rules\n"
    out = generate_agent_compose.apply_overrides(base, override)
    assert "fresh rules" in out
    assert "old sub" not in out  # ### child absorbed by the ## override
    assert "tail" in out  # next ## section preserved


def test_apply_overrides_ambiguous_heading_raises() -> None:
    base = "## Dup\none\n\n## Dup\ntwo\n"
    with pytest.raises(RuntimeError):
        generate_agent_compose.apply_overrides(base, "## Dup\nmerged\n")


def test_discover_override_finds_sibling(tmp_path: Path) -> None:
    base = tmp_path / "AGENTS.md"
    write(base, "## A\nx\n")
    write(tmp_path / "AGENTS.codex.md", "## A\ny\n")
    assert (
        generate_agent_compose.discover_override(base, "codex")
        == tmp_path / "AGENTS.codex.md"
    )
    assert generate_agent_compose.discover_override(base, "claude") is None


def test_run_applies_override_to_one_harness(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    base = tmp_path / "AGENTS.md"
    write(base, "## Shared\nshared\n\n## Reading\nwhole file\n")
    write(tmp_path / "AGENTS.codex.md", "## Reading\nslices only\n")
    write(
        paths["config"],
        f"sources:\n  - {base}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )

    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0

    claude_output = tmp_path / "composed.claude.md"
    codex_output = tmp_path / "composed.codex.md"
    # the override alone forces divergent per-harness outputs
    assert not paths["composed"].exists()
    codex_text = codex_output.read_text(encoding="utf-8")
    claude_text = claude_output.read_text(encoding="utf-8")
    assert "slices only" in codex_text
    assert "whole file" not in codex_text
    assert "whole file" in claude_text  # claude keeps the base section
    assert "shared" in codex_text and "shared" in claude_text


def test_override_makes_check_pass_then_detects_drift(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    base = tmp_path / "AGENTS.md"
    write(base, "## Shared\nshared\n\n## Reading\nwhole file\n")
    write(tmp_path / "AGENTS.codex.md", "## Reading\nslices only\n")
    write(
        paths["config"],
        f"sources:\n  - {base}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    generate_agent_compose.run(paths["config"], paths["composed"])
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 0

    # editing the override re-drifts the codex slice
    write(tmp_path / "AGENTS.codex.md", "## Reading\ngrep then slice\n")
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 1


# ---------- repo-local conventions rewritten for the composed context (#192) ----------


def test_strip_navigation_sections_drops_see_also() -> None:
    body = (
        "# Doctrine\nrule one\n\n"
        "## See also\n- [README.md](README.md)\n\ncross-ref line\n"
    )
    out = generate_agent_compose.strip_navigation_sections(body)
    assert "## See also" not in out
    assert "README.md" not in out
    assert "cross-ref line" not in out  # trailing prose leaves with the section
    assert "# Doctrine" in out and "rule one" in out


def test_strip_navigation_is_case_insensitive_and_keeps_siblings() -> None:
    body = "## Keep\nkept\n\n## SEE ALSO\n- [x](x.md)\n\n## After\ntail\n"
    out = generate_agent_compose.strip_navigation_sections(body)
    assert "## SEE ALSO" not in out
    # a same-level heading after See also is a sibling, not absorbed
    assert "## Keep" in out and "kept" in out
    assert "## After" in out and "tail" in out


def test_absolutize_links_resolves_relative_targets(tmp_path: Path) -> None:
    base = tmp_path / "repo"
    out = generate_agent_compose.absolutize_links("see [readme](README.md) now", base)
    assert f"]({base / 'README.md'})" in out


def test_absolutize_links_leaves_global_targets(tmp_path: Path) -> None:
    body = (
        "[site](https://example.com) [root](/etc/hosts) "
        "[anchor](#scope) [mail](mailto:x@y.z)"
    )
    assert generate_agent_compose.absolutize_links(body, tmp_path / "repo") == body


def test_absolutize_links_preserves_fragment(tmp_path: Path) -> None:
    base = tmp_path / "repo"
    out = generate_agent_compose.absolutize_links("[t](docs/F.md#frag)", base)
    assert f"]({base / 'docs' / 'F.md'}#frag)" in out


def test_compose_rewrites_see_also_and_links(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(
        src,
        "# Doctrine\nRoute through [ward](.ward/ward.yaml).\n\n"
        "## See also\n- [README.md](README.md)\n",
    )
    out = generate_agent_compose.compose([src])
    assert "## See also" not in out
    assert "](README.md)" not in out
    # the inline relative link is absolutized against the source's own dir
    assert f"]({tmp_path / '.ward' / 'ward.yaml'})" in out


def test_compose_strips_see_also_from_overridden_base(tmp_path: Path) -> None:
    base = tmp_path / "AGENTS.COMPOSE.md"
    write(base, "## Reading\nwhole file\n\n## See also\n- [r](README.md)\n")
    override = tmp_path / "AGENTS.codex.md"
    write(override, "## Reading\nslices only\n")
    out = generate_agent_compose.compose([base], {base: override})
    assert "slices only" in out  # override applied
    assert "## See also" not in out  # nav stripped after the merge


# ---------- mount-eligibility manifest (forgejo #222) ----------


def _read_manifest(composed_path: Path) -> dict:
    manifest_path = generate_agent_compose.manifest_path_for(composed_path)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def test_repo_for_source_maps_to_org_repo(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    src = projects / "coilysiren" / "repo-recall" / "sub" / "AGENTS.COMPOSE.md"
    write(src, "x\n")
    assert generate_agent_compose.repo_for_source(src, projects) == (
        projects / "coilysiren" / "repo-recall"
    )


def test_repo_for_source_outside_projects_is_none(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    projects.mkdir()
    outside = tmp_path / "elsewhere" / "AGENTS.COMPOSE.md"
    write(outside, "x\n")
    assert generate_agent_compose.repo_for_source(outside, projects) is None


def test_repo_for_source_above_repo_root_is_none(tmp_path: Path) -> None:
    # A loose source directly under an org dir backs no mountable repo.
    projects = tmp_path / "projects"
    src = projects / "coilysiren" / "AGENTS.COMPOSE.md"
    write(src, "x\n")
    assert generate_agent_compose.repo_for_source(src, projects) is None


def test_run_emits_manifest_with_defaults(
    paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projects = tmp_path / "projects"
    monkeypatch.setenv("PROJECTS_ROOT", str(projects))
    src = projects / "coilysiren" / "repo-recall" / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {src}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )

    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0

    manifest = _read_manifest(paths["composed"])
    assert manifest["projects_root"] == str(projects)
    defaults = [str(projects / slug) for slug in generate_agent_compose.DEFAULT_MOUNT_SET]
    assert manifest["defaults"] == defaults
    repo = str(projects / "coilysiren" / "repo-recall")
    # every harness gets the default mount set plus the eligible repo
    for harness in ("claude", "codex"):
        assert set(manifest["harnesses"][harness]) == set(defaults) | {repo}
        assert manifest["harnesses"][harness] == sorted(manifest["harnesses"][harness])


def test_manifest_honors_harness_filtering(
    paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # claude mounts everything; codex only the flight-deck repo.
    projects = tmp_path / "projects"
    monkeypatch.setenv("PROJECTS_ROOT", str(projects))
    shared = projects / "coilyco-flight-deck" / "ward" / "AGENTS.COMPOSE.md"
    write(shared, "# shared\n")
    claude_only = projects / "coilysiren" / "repo-recall" / "AGENTS.COMPOSE.md"
    write(claude_only, "---\nharnesses: [claude]\n---\n# claude only\n")
    write(
        paths["config"],
        f"sources:\n  - {shared}\n  - {claude_only}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )

    rc = generate_agent_compose.run(paths["config"], paths["composed"])
    assert rc == 0

    manifest = _read_manifest(paths["composed"])
    ward_repo = str(projects / "coilyco-flight-deck" / "ward")
    recall_repo = str(projects / "coilysiren" / "repo-recall")
    assert ward_repo in manifest["harnesses"]["claude"]
    assert recall_repo in manifest["harnesses"]["claude"]
    assert ward_repo in manifest["harnesses"]["codex"]
    assert recall_repo not in manifest["harnesses"]["codex"]


def test_manifest_drift_detected_and_passes_when_synced(
    paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projects = tmp_path / "projects"
    monkeypatch.setenv("PROJECTS_ROOT", str(projects))
    src = projects / "coilysiren" / "repo-recall" / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {src}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )

    assert generate_agent_compose.run(paths["config"], paths["composed"]) == 0
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 0

    # Hand-edit the manifest: the drift check must fail.
    manifest_path = generate_agent_compose.manifest_path_for(paths["composed"])
    manifest_path.write_text("{}\n", encoding="utf-8")
    assert generate_agent_compose.check(paths["config"], paths["composed"]) == 1


def test_dry_run_announces_manifest_and_writes_nothing(
    paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projects = tmp_path / "projects"
    monkeypatch.setenv("PROJECTS_ROOT", str(projects))
    src = projects / "coilysiren" / "repo-recall" / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {src}\n"
        f"load_points:\n  claude: {paths['claude']}\n",
    )

    rc = generate_agent_compose.run(paths["config"], paths["composed"], dry_run=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "mount-eligibility manifest" in out
    assert not generate_agent_compose.manifest_path_for(paths["composed"]).exists()

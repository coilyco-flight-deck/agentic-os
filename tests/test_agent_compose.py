"""Tests for agentic_os.agent_compose: the opt-in composer spine (forgejo #135)."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os import agent_compose


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
        agent_compose,
        "DEFAULT_LOAD_POINTS",
        {"claude": safe / "claude" / "CLAUDE.md", "codex": safe / "codex" / "AGENTS.md"},
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


# ---------- load-point resolution: defaults + opt-in opencode ----------

def test_opencode_skipped_when_unset() -> None:
    points = agent_compose.resolve_load_points({})
    assert set(points) == {"claude", "codex"}


def test_opencode_included_when_set(tmp_path: Path) -> None:
    oc = tmp_path / "opencode" / "AGENTS.md"
    points = agent_compose.resolve_load_points({"load_points": {"opencode": str(oc)}})
    assert points["opencode"] == oc


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
    write(
        src,
        "---\nscopes: [kai-public]\nharnesses: [claude]\n---\n"
        "# doctrine\nrule one\n",
    )
    out = agent_compose.compose([src])
    assert "scopes:" not in out
    assert "harnesses:" not in out
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


# ---------- harness slices ----------

def test_source_harnesses_reads_allowlist(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "---\nharnesses: [claude, codex]\n---\nx\n")
    assert agent_compose.source_harnesses(src) == ["claude", "codex"]


def test_source_without_harnesses_is_shared(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(src, "shared\n")
    assert agent_compose.select_by_harness([src], "codex") == [src]


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

    assert agent_compose.run(paths["config"], paths["composed"]) == 0

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
    assert agent_compose.run(paths["config"], paths["composed"]) == 1
    assert not paths["claude"].exists()
    assert not paths["codex"].exists()


def test_run_removes_obsolete_shared_output(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    shared = tmp_path / "shared.md"
    claude_only = tmp_path / "claude.md"
    write(shared, "shared doctrine\n")
    write(paths["config"], f"sources:\n  - {shared}\n")
    assert agent_compose.run(paths["config"], paths["composed"]) == 0
    assert paths["composed"].exists()

    write(claude_only, "---\nharnesses: [claude]\n---\nclaude doctrine\n")
    write(
        paths["config"],
        f"sources:\n  - {shared}\n  - {claude_only}\n"
        f"load_points:\n  claude: {paths['claude']}\n  codex: {paths['codex']}\n",
    )
    assert agent_compose.run(paths["config"], paths["composed"]) == 0
    assert not paths["composed"].exists()


def test_run_preserves_similarly_named_user_file(
    paths: dict[str, Path], tmp_path: Path
) -> None:
    src = tmp_path / "shared.md"
    user_file = tmp_path / "composed.notes.md"
    write(src, "shared doctrine\n")
    write(user_file, "user-owned notes\n")
    write(paths["config"], f"sources:\n  - {src}\n")
    assert agent_compose.run(paths["config"], paths["composed"]) == 0
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
    agent_compose.run(paths["config"], paths["composed"])
    (tmp_path / "composed.codex.md").write_text("drift\n", encoding="utf-8")
    assert agent_compose.check(paths["config"], paths["composed"]) == 1


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
    agent_compose.run(paths["config"], paths["composed"])
    write(paths["composed"], agent_compose.compose([shared]))
    assert agent_compose.check(paths["config"], paths["composed"]) == 1


# ---------- per-harness section overrides ----------

def test_apply_overrides_replaces_matching_section() -> None:
    base = "## Keep\nkeep me\n\n## Reading\nread the whole file\n"
    override = "## Reading\nread slices only\n"
    out = agent_compose.apply_overrides(base, override)
    assert "read slices only" in out
    assert "read the whole file" not in out
    assert "keep me" in out  # untouched section survives


def test_apply_overrides_appends_new_section() -> None:
    base = "## Keep\nkeep me\n"
    override = "## Reading\nread slices only\n"
    out = agent_compose.apply_overrides(base, override)
    assert "keep me" in out
    assert out.strip().endswith("read slices only")


def test_apply_overrides_section_absorbs_subsections() -> None:
    base = "## Rules\nintro\n### Sub\nold sub\n\n## After\ntail\n"
    override = "## Rules\nfresh rules\n"
    out = agent_compose.apply_overrides(base, override)
    assert "fresh rules" in out
    assert "old sub" not in out  # ### child absorbed by the ## override
    assert "tail" in out  # next ## section preserved


def test_apply_overrides_ambiguous_heading_raises() -> None:
    base = "## Dup\none\n\n## Dup\ntwo\n"
    with pytest.raises(RuntimeError):
        agent_compose.apply_overrides(base, "## Dup\nmerged\n")


def test_discover_override_finds_sibling(tmp_path: Path) -> None:
    base = tmp_path / "AGENTS.md"
    write(base, "## A\nx\n")
    write(tmp_path / "AGENTS.codex.md", "## A\ny\n")
    assert agent_compose.discover_override(base, "codex") == tmp_path / "AGENTS.codex.md"
    assert agent_compose.discover_override(base, "claude") is None


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

    assert agent_compose.run(paths["config"], paths["composed"]) == 0

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
    agent_compose.run(paths["config"], paths["composed"])
    assert agent_compose.check(paths["config"], paths["composed"]) == 0

    # editing the override re-drifts the codex slice
    write(tmp_path / "AGENTS.codex.md", "## Reading\ngrep then slice\n")
    assert agent_compose.check(paths["config"], paths["composed"]) == 1


# ---------- repo-local conventions rewritten for the composed context (#192) ----------

def test_strip_navigation_sections_drops_see_also() -> None:
    body = (
        "# Doctrine\nrule one\n\n"
        "## See also\n- [README.md](README.md)\n\ncross-ref line\n"
    )
    out = agent_compose.strip_navigation_sections(body)
    assert "## See also" not in out
    assert "README.md" not in out
    assert "cross-ref line" not in out  # trailing prose leaves with the section
    assert "# Doctrine" in out and "rule one" in out


def test_strip_navigation_is_case_insensitive_and_keeps_siblings() -> None:
    body = "## Keep\nkept\n\n## SEE ALSO\n- [x](x.md)\n\n## After\ntail\n"
    out = agent_compose.strip_navigation_sections(body)
    assert "## SEE ALSO" not in out
    # a same-level heading after See also is a sibling, not absorbed
    assert "## Keep" in out and "kept" in out
    assert "## After" in out and "tail" in out


def test_absolutize_links_resolves_relative_targets(tmp_path: Path) -> None:
    base = tmp_path / "repo"
    out = agent_compose.absolutize_links("see [readme](README.md) now", base)
    assert f"]({base / 'README.md'})" in out


def test_absolutize_links_leaves_global_targets(tmp_path: Path) -> None:
    body = (
        "[site](https://example.com) [root](/etc/hosts) "
        "[anchor](#scope) [mail](mailto:x@y.z)"
    )
    assert agent_compose.absolutize_links(body, tmp_path / "repo") == body


def test_absolutize_links_preserves_fragment(tmp_path: Path) -> None:
    base = tmp_path / "repo"
    out = agent_compose.absolutize_links("[t](docs/F.md#frag)", base)
    assert f"]({base / 'docs' / 'F.md'}#frag)" in out


def test_compose_rewrites_see_also_and_links(tmp_path: Path) -> None:
    src = tmp_path / "AGENTS.COMPOSE.md"
    write(
        src,
        "# Doctrine\nRoute through [coily](.coily/coily.yaml).\n\n"
        "## See also\n- [README.md](README.md)\n",
    )
    out = agent_compose.compose([src])
    assert "## See also" not in out
    assert "](README.md)" not in out
    # the inline relative link is absolutized against the source's own dir
    assert f"]({tmp_path / '.coily' / 'coily.yaml'})" in out


def test_compose_strips_see_also_from_overridden_base(tmp_path: Path) -> None:
    base = tmp_path / "AGENTS.COMPOSE.md"
    write(base, "## Reading\nwhole file\n\n## See also\n- [r](README.md)\n")
    override = tmp_path / "AGENTS.codex.md"
    write(override, "## Reading\nslices only\n")
    out = agent_compose.compose([base], {base: override})
    assert "slices only" in out  # override applied
    assert "## See also" not in out  # nav stripped after the merge

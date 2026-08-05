"""Tests for the on-demand context-budget report."""
from __future__ import annotations

import json
from pathlib import Path

from agentic_os.pre_commit import check_context_budget as budget


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_count_tokens_is_chars_over_four_ceil() -> None:
    assert budget.count_tokens("") == 0
    assert budget.count_tokens("x" * 4) == 1
    assert budget.count_tokens("x" * 5) == 2  # ceil, not floor


def test_skill_contributions_counts_frontmatter_and_dedups(tmp_path: Path) -> None:
    # Two skills under an absolute root.
    write(
        tmp_path / "skills" / "alpha" / "SKILL.md",
        "---\nname: alpha\ndescription: does alpha things\n---\nbody\n",
    )
    write(
        tmp_path / "skills" / "beta" / "SKILL.md",
        "---\nname: beta\ndescription: " + "x" * 200 + "\n---\nbody\n",
    )
    total, top, count = budget.skill_contributions([str(tmp_path / "skills")], tmp_path)
    assert count == 2
    assert total > 0
    assert top[0][0] == "beta"  # longer description ranks first


def test_skill_contributions_dedups_symlinked_set(tmp_path: Path) -> None:
    # A canonical skill symlinked into two repos counts once.
    canon = tmp_path / "canonical" / "gamma" / "SKILL.md"
    write(canon, "---\nname: gamma\ndescription: shared\n---\n")
    for repo in ("repoA", "repoB"):
        link_dir = tmp_path / repo / ".claude" / "skills"
        link_dir.mkdir(parents=True)
        (link_dir / "gamma").symlink_to(canon.parent)
    _total, _top, count = budget.skill_contributions(
        [str(tmp_path / "repoA" / ".claude" / "skills"),
         str(tmp_path / "repoB" / ".claude" / "skills")],
        tmp_path,
    )
    assert count == 1  # deduped by resolved path


def _git_repo(path: Path) -> None:
    """Init a git repo at path and stage every file currently in it."""
    import subprocess

    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)


def test_immediate_walk_counts_tracked_only(tmp_path: Path) -> None:
    repo = tmp_path / "clone"
    write(repo / "a.txt", "x" * 40)  # 40 chars -> 10 tokens
    write(repo / "sub" / "b.txt", "y" * 8)  # 8 chars -> 2 tokens
    _git_repo(repo)
    # An untracked build tree must not inflate the walk.
    write(repo / "build" / "huge.bin", "z" * 10_000)
    walk = budget.immediate_walk(repo)
    assert walk.files == 2
    assert walk.bytes == 48
    assert walk.tokens == 12


def test_immediate_walk_non_repo_is_zero(tmp_path: Path) -> None:
    walk = budget.immediate_walk(tmp_path / "not-a-repo")
    assert walk == budget.TierWalk(0, 0, 0)


def test_peripheral_walk_totals_across_repos(tmp_path: Path) -> None:
    for name, blob in (("refA", "a" * 40), ("refB", "b" * 80)):
        repo = tmp_path / name
        write(repo / "f.txt", blob)
        _git_repo(repo)
    total, per_repo = budget.peripheral_walk([tmp_path / "refA", tmp_path / "refB"])
    names = {n for n, _w in per_repo}
    assert names == {"refA", "refB"}
    assert total.files == 2
    assert total.bytes == 120
    assert total.tokens == sum(w.tokens for _n, w in per_repo)


def test_tier_section_empty_without_paths() -> None:
    assert budget.tier_section([], []) == []


def test_read_mcporter_servers(tmp_path: Path) -> None:
    cfg = tmp_path / "mcporter.json"
    write(cfg, json.dumps({"mcpServers": {"terraform": {}, "sentry": {}}}))
    assert budget.read_mcporter_servers(cfg) == ["sentry", "terraform"]
    assert budget.read_mcporter_servers(tmp_path / "missing.json") is None


def test_codex_skill_roots_use_portable_standard() -> None:
    assert budget.DEFAULT_SKILL_ROOTS["codex"] == [
        "~/.agents/skills",
        ".agents/skills",
    ]


def test_run_end_to_end(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "agent-compose.yaml"
    write(config_path, "sources: []\n")
    nomcp = tmp_path / "no-mcp.json"
    monkeypatch.setattr(
        budget,
        "DEFAULT_LOAD_POINTS",
        {"claude": tmp_path / "missing-CLAUDE.md"},
    )
    monkeypatch.setattr(budget, "DEFAULT_SKILL_ROOTS", {"claude": []})
    # Report mode always exits 0.
    assert budget.run(config_path, {}, nomcp, tmp_path, check=False) == 0
    # With no installed load point, a tiny document budget still passes.
    assert budget.run(config_path, {"claude": 1}, nomcp, tmp_path, check=True) == 0
    # Tier walk paths flow through run without disturbing the exit code.
    clone = tmp_path / "clone"
    write(clone / "f.txt", "x" * 20)
    _git_repo(clone)
    assert (
        budget.run(
            config_path, {}, nomcp, tmp_path, check=False,
            immediate=[clone], peripheral=[clone],
        )
        == 0
    )

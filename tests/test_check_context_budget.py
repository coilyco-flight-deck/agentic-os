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


def test_doc_contributions_ranks_sources(tmp_path: Path) -> None:
    big = tmp_path / "big" / "AGENTS.COMPOSE.md"
    small = tmp_path / "small" / "AGENTS.COMPOSE.md"
    write(big, "# big\n" + "x" * 400)
    write(small, "# small\n" + "y" * 40)
    total, per_source = budget.doc_contributions([big, small], {})
    assert total > 0
    assert per_source[0][0] == str(big)  # 400-char source leads
    assert per_source[0][1] >= per_source[1][1]


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


def test_read_mcporter_servers(tmp_path: Path) -> None:
    cfg = tmp_path / "mcporter.json"
    write(cfg, json.dumps({"mcpServers": {"terraform": {}, "sentry": {}}}))
    assert budget.read_mcporter_servers(cfg) == ["sentry", "terraform"]
    assert budget.read_mcporter_servers(tmp_path / "missing.json") is None


def test_plan_from_config_none_when_absent(tmp_path: Path) -> None:
    assert budget.plan_from_config(tmp_path / "no-config.yaml", tmp_path / "C.md") is None


def test_skill_roots_from_config_overlay(tmp_path: Path) -> None:
    cfg = tmp_path / "agent-compose.yaml"
    write(cfg, "skill_roots:\n  claude:\n    - /custom/skills\n")
    roots = budget.skill_roots_from_config(cfg)
    assert roots["claude"] == ["/custom/skills"]
    assert "codex" in roots  # untouched harnesses keep defaults


def test_run_end_to_end(tmp_path: Path) -> None:
    src = tmp_path / "repo" / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\n" + "x" * 800)
    config_path = tmp_path / "agent-compose.yaml"
    write(
        config_path,
        f"sources:\n  - {src}\n"
        f"load_points:\n  claude: {tmp_path / 'CLAUDE.md'}\n  codex: null\n"
        f"skill_roots:\n  claude: []\n",  # isolate doc axis for a deterministic budget test
    )
    composed = tmp_path / "COMPOSED.md"
    nomcp = tmp_path / "no-mcp.json"
    # Report mode always exits 0.
    assert budget.run(config_path, composed, {}, nomcp, tmp_path, check=False) == 0
    # Check mode exits 1 when forced over a tiny budget.
    assert budget.run(config_path, composed, {"claude": 1}, nomcp, tmp_path, check=True) == 1

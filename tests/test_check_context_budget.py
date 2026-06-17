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


def test_harness_contributions_ranks_sources(tmp_path: Path) -> None:
    big = tmp_path / "big" / "AGENTS.COMPOSE.md"
    small = tmp_path / "small" / "AGENTS.COMPOSE.md"
    write(big, "# big\n" + "x" * 400)
    write(small, "# small\n" + "y" * 40)
    total, per_source = budget.harness_contributions([big, small], {})
    assert total > 0
    # Sorted biggest-first, so the 400-char source leads.
    assert per_source[0][0] == big
    assert per_source[0][1] >= per_source[1][1]


def test_build_report_flags_over_budget(tmp_path: Path) -> None:
    src = tmp_path / "repo" / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\n" + "x" * 800)
    load_points = {"claude": tmp_path / "CLAUDE.md"}
    lines, over = budget.build_report(
        {"claude": load_points["claude"]},
        {"claude": [src]},
        {"claude": {}},
        {"claude": 10},  # tiny budget, guaranteed over
    )
    assert over == ["claude"]
    assert any("OVER by" in line for line in lines)


def test_build_report_under_budget_is_clean(tmp_path: Path) -> None:
    src = tmp_path / "repo" / "AGENTS.COMPOSE.md"
    write(src, "# tiny\n")
    _lines, over = budget.build_report(
        {"claude": tmp_path / "CLAUDE.md"},
        {"claude": [src]},
        {"claude": {}},
        {"claude": 100_000},
    )
    assert over == []


def test_read_mcporter_servers(tmp_path: Path) -> None:
    cfg = tmp_path / "mcporter.json"
    write(cfg, json.dumps({"mcpServers": {"terraform": {}, "sentry": {}}}))
    assert budget.read_mcporter_servers(cfg) == ["sentry", "terraform"]
    assert budget.read_mcporter_servers(tmp_path / "missing.json") is None


def test_plan_from_config_none_when_absent(tmp_path: Path) -> None:
    assert budget.plan_from_config(tmp_path / "no-config.yaml", tmp_path / "C.md") is None


def test_run_end_to_end(tmp_path: Path) -> None:
    src = tmp_path / "repo" / "AGENTS.COMPOSE.md"
    write(src, "# doctrine\n" + "x" * 800)
    config_path = tmp_path / "agent-compose.yaml"
    write(
        config_path,
        f"sources:\n  - {src}\n"
        f"load_points:\n  claude: {tmp_path / 'CLAUDE.md'}\n  codex: null\n",
    )
    composed = tmp_path / "COMPOSED.md"
    # Report mode always exits 0.
    assert budget.run(config_path, composed, {}, tmp_path / "no-mcp.json", check=False) == 0
    # Check mode exits 1 when forced over a tiny budget.
    assert (
        budget.run(config_path, composed, {"claude": 1}, tmp_path / "no-mcp.json", check=True)
        == 1
    )

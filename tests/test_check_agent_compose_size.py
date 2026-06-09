"""Tests for the agent-compose-size validator (forgejo #138)."""
from __future__ import annotations

from pathlib import Path

from agentic_os.pre_commit import check_agent_compose_size as size


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_no_sources_is_clean(tmp_path: Path) -> None:
    write(tmp_path / "AGENTS.md", "not a source\n")
    assert size.find_violations(tmp_path) == []


def test_under_budget_clean(tmp_path: Path) -> None:
    write(tmp_path / "repo" / "AGENTS.COMPOSE.md", "x" * 100)
    assert size.find_violations(tmp_path) == []


def test_per_source_cap(tmp_path: Path) -> None:
    write(tmp_path / "repo" / "AGENTS.COMPOSE.md", "x" * (size.DEFAULT_MAX_SOURCE_CHARS + 1))
    violations = size.find_violations(tmp_path)
    assert any("per-source cap" in v for v in violations)


def test_aggregate_budget(tmp_path: Path) -> None:
    # Two files each under the per-source cap but together over the total budget.
    half = size.DEFAULT_MAX_SOURCE_CHARS - 10
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", "x" * half)
    write(tmp_path / "b" / "AGENTS.COMPOSE.md", "y" * half)
    write(tmp_path / "c" / "AGENTS.COMPOSE.md", "z" * half)
    write(tmp_path / "d" / "AGENTS.COMPOSE.md", "w" * half)
    violations = size.find_violations(tmp_path)
    assert any("budget" in v for v in violations)
    assert not any("per-source cap" in v for v in violations)


def test_config_overrides(tmp_path: Path) -> None:
    write(tmp_path / "repo" / "AGENTS.COMPOSE.md", "x" * 200)
    write(
        tmp_path / "pyproject.toml",
        "[tool.agentic-os.agent-compose-size]\nmax_source_chars = 50\n",
    )
    assert any("per-source cap" in v for v in size.find_violations(tmp_path))


def test_skips_dot_dirs(tmp_path: Path) -> None:
    write(tmp_path / ".git" / "AGENTS.COMPOSE.md", "x" * (size.DEFAULT_MAX_SOURCE_CHARS + 1))
    assert size.find_violations(tmp_path) == []

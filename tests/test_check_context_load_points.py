"""Tests for agentic_os.check_context_load_points: the AGENTS/CLAUDE framework."""
from __future__ import annotations

import os
from pathlib import Path

from agentic_os.check_context_load_points import (
    find_violations,
    imports_of,
    is_pure_pointer,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def canonical_repo(root: Path) -> None:
    """A compliant repo: root AGENTS.md + `@AGENTS.md` CLAUDE.md bridge."""
    write(root / "AGENTS.md", "# Agents\n\nDoctrine here.\n")
    write(root / "CLAUDE.md", "@AGENTS.md\n")


def test_pure_pointer_predicate() -> None:
    assert is_pure_pointer("@AGENTS.md\n")
    assert is_pure_pointer("\n@AGENTS.md\n\n")
    assert is_pure_pointer("@../agentic-os/AGENTS.md\n@AGENTS.md\n")
    assert not is_pure_pointer("# Memory\n\nKai likes factory games.\n")
    assert not is_pure_pointer("@AGENTS.md\nplus a trailing note\n")


def test_imports_of() -> None:
    assert imports_of("@AGENTS.md\n") == ["AGENTS.md"]
    assert imports_of("@../base/AGENTS.md\n@AGENTS.md\n") == [
        "../base/AGENTS.md",
        "AGENTS.md",
    ]
    assert imports_of("# heading\n") == []


def test_canonical_repo_is_clean(tmp_path: Path) -> None:
    canonical_repo(tmp_path)
    assert find_violations(tmp_path) == []


def test_forked_claude_md_fails(tmp_path: Path) -> None:
    write(tmp_path / "AGENTS.md", "# Agents\n")
    write(tmp_path / "CLAUDE.md", "# Memory\n\nForked doctrine.\n")
    problems = find_violations(tmp_path)
    assert any("pure @-import pointer" in p for p in problems)


def test_missing_bridge_fails(tmp_path: Path) -> None:
    write(tmp_path / "AGENTS.md", "# Agents\n")
    problems = find_violations(tmp_path)
    assert any("no CLAUDE.md bridge" in p for p in problems)


def test_claude_not_importing_agents_fails(tmp_path: Path) -> None:
    write(tmp_path / "AGENTS.md", "# Agents\n")
    write(tmp_path / "CLAUDE.md", "@../somewhere/OTHER.md\n")
    problems = find_violations(tmp_path)
    assert any("bridge to AGENTS.md" in p for p in problems)


def test_forked_rung_in_subdir_fails(tmp_path: Path) -> None:
    canonical_repo(tmp_path)
    write(tmp_path / "sub" / "AGENTS.md", "# Forked\n")
    problems = find_violations(tmp_path)
    assert any("sub/AGENTS.md" in p and "repo root" in p for p in problems)


def test_symlinked_rung_in_subdir_is_allowed(tmp_path: Path) -> None:
    canonical_repo(tmp_path)
    workspace = tmp_path / "openclaw"
    workspace.mkdir()
    os.symlink(tmp_path / "AGENTS.md", workspace / "AGENTS.md")
    assert find_violations(tmp_path) == []


def test_load_point_in_skill_folder_is_allowed(tmp_path: Path) -> None:
    canonical_repo(tmp_path)
    # A skill documenting an example AGENTS.md, not a loaded rung.
    write(tmp_path / ".agents" / "skills" / "demo" / "AGENTS.md", "# Example\n")
    assert find_violations(tmp_path) == []


def test_load_point_under_examples_is_allowed(tmp_path: Path) -> None:
    canonical_repo(tmp_path)
    write(tmp_path / "examples" / "starter" / "CLAUDE.md", "# Sample\n")
    assert find_violations(tmp_path) == []


def test_repo_without_agents_md_is_clean(tmp_path: Path) -> None:
    # No AGENTS.md, no CLAUDE.md: the bridge requirement does not apply.
    write(tmp_path / "README.md", "# Hello\n")
    assert find_violations(tmp_path) == []

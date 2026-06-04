"""Tests for agentic_os.check_documentation_layout skill flatness rule.

The flatness rule targets nested sub-skills (a SKILL.md the loader can't see),
not support material that legitimately sits beside SKILL.md.
"""
from __future__ import annotations

from pathlib import Path

from agentic_os.check_documentation_layout import (
    ROOT_MARKDOWN_ALLOWLIST,
    check_skill_flatness,
)


def test_agents_compose_md_is_an_allowed_root_file() -> None:
    # agent-compose's disjoint source is a repo-root convention; the layout
    # rule must not reject it the way it rejects one-off root Markdown.
    assert "AGENTS.COMPOSE.md" in ROOT_MARKDOWN_ALLOWLIST


def write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_support_subdirs_are_allowed(tmp_path: Path) -> None:
    skill = tmp_path / ".agents" / "skills" / "my-skill"
    write(skill / "SKILL.md")
    write(skill / "scripts" / "run.sh")
    write(skill / "assets" / "logo.png")
    write(skill / "agents" / "openai.yaml")
    write(skill / "references" / "deep.md")
    assert check_skill_flatness(tmp_path) == []


def test_nested_skill_md_is_flagged(tmp_path: Path) -> None:
    skill = tmp_path / ".agents" / "skills" / "my-skill"
    write(skill / "SKILL.md")
    write(skill / "sub-skill" / "SKILL.md")
    problems = check_skill_flatness(tmp_path)
    assert len(problems) == 1
    assert "sub-skill/SKILL.md" in problems[0]
    assert "nested SKILL.md" in problems[0]


def test_top_level_skill_md_is_clean(tmp_path: Path) -> None:
    for name in ("a", "b", "c"):
        write(tmp_path / ".agents" / "skills" / name / "SKILL.md")
    assert check_skill_flatness(tmp_path) == []


def test_nested_skill_md_can_be_excluded(tmp_path: Path) -> None:
    skill = tmp_path / ".agents" / "skills" / "my-skill"
    write(skill / "SKILL.md")
    write(skill / "vendor" / "SKILL.md")
    write(
        tmp_path / "pyproject.toml",
        '[tool.agentic-os.documentation-layout]\n'
        'excludes = [".agents/skills/my-skill/vendor/**"]\n',
    )
    assert check_skill_flatness(tmp_path) == []

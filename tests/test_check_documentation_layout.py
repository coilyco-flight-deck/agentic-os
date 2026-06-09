"""Tests for agentic_os.pre_commit.check_documentation_layout skill flatness rule.

The flatness rule targets nested sub-skills (a SKILL.md the loader can't see),
not support material that legitimately sits beside SKILL.md.
"""
from __future__ import annotations

from pathlib import Path

from agentic_os.pre_commit.check_documentation_layout import (
    ROOT_MARKDOWN_ALLOWLIST,
    check_skill_flatness,
    is_harness_override,
    validate_module_readme,
)


def test_agents_compose_md_is_an_allowed_root_file() -> None:
    # agent-compose's disjoint source is a repo-root convention; the layout
    # rule must not reject it the way it rejects one-off root Markdown.
    assert "AGENTS.COMPOSE.md" in ROOT_MARKDOWN_ALLOWLIST


def test_harness_override_filenames_are_recognized() -> None:
    # AGENTS.<harness>.md overrides sit at repo root beside AGENTS.md.
    assert is_harness_override("AGENTS.codex.md")
    assert is_harness_override("AGENTS.claude.md")
    # not overrides: the uppercase disjoint source, the base, one-off docs.
    assert not is_harness_override("AGENTS.COMPOSE.md")
    assert not is_harness_override("AGENTS.md")
    assert not is_harness_override("notes.md")


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


# Module README.md: outpost / homestead shapes. validate_module_readme takes a
# repo-relative README path and the repo root, returning [] when valid.

def readme(text: str) -> str:
    return text


def test_valid_outpost_with_reciprocal_docs(tmp_path: Path) -> None:
    write(
        tmp_path / "ansible" / "README.md",
        "# Ansible\nConverges workstation state.\n"
        "Full runbook: [docs/ansible.md](../docs/ansible.md)\n",
    )
    write(tmp_path / "docs" / "ansible.md", "# Ansible\nSee [ansible/](../ansible/README.md).\n")
    assert validate_module_readme(Path("ansible/README.md"), tmp_path) == []


def test_outpost_without_back_link_is_flagged(tmp_path: Path) -> None:
    write(
        tmp_path / "ansible" / "README.md",
        "# Ansible\n[docs/ansible.md](../docs/ansible.md)\n",
    )
    write(tmp_path / "docs" / "ansible.md", "# Ansible\nNo link back here.\n")
    problems = validate_module_readme(Path("ansible/README.md"), tmp_path)
    assert len(problems) == 1
    assert "not reciprocal" in problems[0]


def test_outpost_pointing_at_missing_doc_is_flagged(tmp_path: Path) -> None:
    write(
        tmp_path / "ansible" / "README.md",
        "# Ansible\n[gone](../docs/ansible.md)\n",
    )
    problems = validate_module_readme(Path("ansible/README.md"), tmp_path)
    assert len(problems) == 1
    assert "does not exist" in problems[0]


def test_outpost_with_two_docs_targets_is_flagged(tmp_path: Path) -> None:
    write(
        tmp_path / "ansible" / "README.md",
        "# Ansible\n[a](../docs/a.md) and [b](../docs/b.md)\n",
    )
    write(tmp_path / "docs" / "a.md", "[x](../ansible/README.md)\n")
    write(tmp_path / "docs" / "b.md", "[x](../ansible/README.md)\n")
    problems = validate_module_readme(Path("ansible/README.md"), tmp_path)
    assert any("exactly one" in p for p in problems)


def test_outpost_pointer_line_exempt_from_char_cap(tmp_path: Path) -> None:
    # A long relative path on the pointer line must not trip the prose cap.
    deep = "deploy/some/very/deeply/nested/module"
    target = "../" * 6 + "docs/deploy-some-very-deeply-nested-module.md"
    write(
        tmp_path / deep / "README.md",
        f"# Module\n[full runbook with a long path]({target})\n",
    )
    write(
        tmp_path / "docs" / "deploy-some-very-deeply-nested-module.md",
        f"# Module\n[x](/{deep}/README.md)\n",
    )
    assert validate_module_readme(Path(f"{deep}/README.md"), tmp_path) == []


def test_valid_homestead(tmp_path: Path) -> None:
    write(
        tmp_path / "eco-server" / "README.md",
        "# Eco server\nVendored game-server tree.\nDo not edit by hand.\n",
    )
    assert validate_module_readme(Path("eco-server/README.md"), tmp_path) == []


def test_homestead_over_line_cap_is_flagged(tmp_path: Path) -> None:
    write(
        tmp_path / "mod" / "README.md",
        "# Mod\nline one\nline two\nline three\n",
    )
    problems = validate_module_readme(Path("mod/README.md"), tmp_path)
    assert any("non-blank lines" in p for p in problems)


def test_blank_lines_do_not_count_toward_line_cap(tmp_path: Path) -> None:
    write(
        tmp_path / "mod" / "README.md",
        "# Mod\n\nVendored tree.\n\nDo not edit.\n",
    )
    assert validate_module_readme(Path("mod/README.md"), tmp_path) == []


def test_homestead_prose_over_char_cap_is_flagged(tmp_path: Path) -> None:
    write(
        tmp_path / "mod" / "README.md",
        "# Mod\n" + "x" * 91 + "\n",
    )
    problems = validate_module_readme(Path("mod/README.md"), tmp_path)
    assert any("chars, max 90" in p for p in problems)


def test_readme_must_lead_with_heading(tmp_path: Path) -> None:
    write(tmp_path / "mod" / "README.md", "just text, no heading\n")
    problems = validate_module_readme(Path("mod/README.md"), tmp_path)
    assert any("heading" in p for p in problems)


def test_root_absolute_back_link_is_reciprocal(tmp_path: Path) -> None:
    # docs file may link back root-absolute (/ansible/README.md), not relative.
    write(
        tmp_path / "ansible" / "README.md",
        "# Ansible\n[runbook](/docs/ansible.md)\n",
    )
    write(tmp_path / "docs" / "ansible.md", "# Ansible\n[home](/ansible/README.md)\n")
    assert validate_module_readme(Path("ansible/README.md"), tmp_path) == []

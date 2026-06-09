"""Tests for the agent-compose-dedup validator (forgejo #139)."""
from __future__ import annotations

from pathlib import Path

from agentic_os.pre_commit import check_agent_compose_dedup as dedup


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


LONG = "always sign commits with the per-host gpg-ssm signing key"


def test_clean_repo(tmp_path: Path) -> None:
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", "unique doctrine line number one here\n")
    write(tmp_path / "b" / "AGENTS.COMPOSE.md", "a totally different rule that stands\n")
    assert dedup.find_violations(tmp_path) == []


def test_duplicate_across_sources(tmp_path: Path) -> None:
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", f"{LONG}\n")
    write(tmp_path / "b" / "AGENTS.COMPOSE.md", f"{LONG}\n")
    violations = dedup.find_violations(tmp_path)
    assert any("duplicated across" in v for v in violations)


def test_duplicate_with_agents_cascade(tmp_path: Path) -> None:
    write(tmp_path / "AGENTS.md", f"{LONG}\n")
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", f"{LONG}\n")
    violations = dedup.find_violations(tmp_path)
    assert any("duplicates AGENTS.md" in v for v in violations)


def test_short_lines_ignored(tmp_path: Path) -> None:
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", "be nice\n")
    write(tmp_path / "b" / "AGENTS.COMPOSE.md", "be nice\n")
    assert dedup.find_violations(tmp_path) == []


def test_markdown_scaffolding_ignored(tmp_path: Path) -> None:
    heading = "## a shared section heading that is long enough to pass length\n"
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", heading)
    write(tmp_path / "b" / "AGENTS.COMPOSE.md", heading)
    assert dedup.find_violations(tmp_path) == []


def test_frontmatter_not_counted(tmp_path: Path) -> None:
    fm = "---\nscopes: [kai-public, work, kai-private]\n---\n"
    write(tmp_path / "a" / "AGENTS.COMPOSE.md", fm + "rule unique to file a goes here\n")
    write(tmp_path / "b" / "AGENTS.COMPOSE.md", fm + "rule unique to file b goes here\n")
    # Identical frontmatter must not be flagged as duplicated content.
    assert dedup.find_violations(tmp_path) == []

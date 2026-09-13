"""Every cap violation carries the sentence that closes the raise request.

Agents read a cap as a defect and open a record asking for a raise. The
message is the only surface present at the moment that happens, so each of
the four cap-enforcing validators appends CAP_IS_DELIBERATE. This test is
the thing that notices when a new cap message ships without it.
"""
from __future__ import annotations

from pathlib import Path

import agentic_os.config as config
import agentic_os.pre_commit.check_agent_compose_size as compose_size
import agentic_os.pre_commit.check_code_comments as comments
import agentic_os.pre_commit.check_documentation_layout as docs_layout
import agentic_os.pre_commit.check_skill as skill
from agentic_os.pre_commit.caps import CAP_IS_DELIBERATE

from tests.test_check_documentation_layout import _point_repo_root_at, write


def test_docs_count_cap_says_not_to_ask(tmp_path: Path, monkeypatch) -> None:
    _point_repo_root_at(tmp_path, monkeypatch)
    for n in range(docs_layout.docs_cap() + 1):
        write(tmp_path / "docs" / f"page{n}.md")
    violations = docs_layout.check_docs_count()
    assert violations
    assert all(CAP_IS_DELIBERATE in v for v in violations)


def test_markdown_size_caps_say_not_to_ask(tmp_path: Path, monkeypatch) -> None:
    _point_repo_root_at(tmp_path, monkeypatch)
    max_lines, max_chars = docs_layout.markdown_caps()
    write(tmp_path / "docs" / "long.md", "line\n" * (max_lines + 1))
    write(tmp_path / "docs" / "wide.md", "x" * (max_chars + 1) + "\n")
    violations = docs_layout.check_markdown_sizes()
    assert [v for v in violations if "-line cap" in v]
    assert [v for v in violations if "-char cap" in v]
    assert all(CAP_IS_DELIBERATE in v for v in violations)


def test_docstring_caps_say_not_to_ask() -> None:
    body = "\n".join(f"    line {n}" for n in range(comments.MAX_DOCSTRING_LINES + 2))
    long_line = "    " + "x" * (comments.MAX_COMMENT_LINE_CHARS + 1)
    source = f'"""head\n{body}\n{long_line}\n"""\n'
    violations = comments.docstring_violations(Path("m.py"), source.splitlines())
    assert [v for v in violations if "-line cap" in v]
    assert [v for v in violations if "-char cap" in v]
    assert all(CAP_IS_DELIBERATE in v for v in violations)


def test_comment_line_and_header_caps_say_not_to_ask() -> None:
    wide = "# " + "x" * comments.MAX_COMMENT_LINE_CHARS
    assert CAP_IS_DELIBERATE in comments.char_cap_violation(Path("m.py"), 1, wide)
    assert CAP_IS_DELIBERATE in comments.header_cap_violation(Path("m.py"), 1, 99)


def test_skill_size_caps_say_not_to_ask(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(skill, "REPO_ROOT", tmp_path)
    md = tmp_path / "SKILL.md"
    md.write_text("line\n" * (skill.THIN_MAX_LINES + skill.THIN_MAX_BYTES), "utf-8")
    report = skill.Report()
    skill.check_size_caps(md, skill.Spec(raw={}), report, role="thin")
    assert [v for v in report.failures if "-line cap" in v]
    assert [v for v in report.failures if "-byte cap" in v]
    assert all(CAP_IS_DELIBERATE in v for v in report.failures)


def test_agent_compose_caps_say_not_to_ask(tmp_path: Path) -> None:
    over = compose_size.DEFAULT_MAX_SOURCE_CHARS + 1
    for name in ("a", "b", "c"):
        target = tmp_path / name / "AGENTS.COMPOSE.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x" * over, encoding="utf-8")
    violations = compose_size.find_violations(tmp_path)
    assert [v for v in violations if "per-source cap" in v]
    assert [v for v in violations if "budget" in v]
    assert all(CAP_IS_DELIBERATE in v for v in violations)


def test_every_cap_validator_imports_the_constant() -> None:
    # A new cap message in a module that never imported it cannot carry it.
    for module in (docs_layout, comments, skill, compose_size):
        assert module.CAP_IS_DELIBERATE is CAP_IS_DELIBERATE


def test_config_module_is_reachable() -> None:
    assert config.REPO_ROOT

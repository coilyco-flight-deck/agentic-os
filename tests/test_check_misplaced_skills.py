"""Tests for agentic_os.pre_commit.check_misplaced_skills: foreign-skill guard."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os import config
from agentic_os.pre_commit.check_misplaced_skills import main, misplaced


def test_misplaced_matches_deny_minus_allow() -> None:
    names = ["coding-otel-a2a-relay", "coding-python", "repo-coily", "repo-self"]
    deny = ["coding-*", "repo-*"]
    allow = ["repo-self"]
    assert misplaced(names, deny, allow) == [
        "coding-otel-a2a-relay",
        "coding-python",
        "repo-coily",
    ]


def test_misplaced_empty_deny_flags_nothing() -> None:
    assert misplaced(["coding-x", "repo-y"], [], []) == []


def _make_skill(skills_dir: Path, name: str) -> None:
    d = skills_dir / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")


def _write_pyproject(root: Path, body: str) -> None:
    (root / "pyproject.toml").write_text(body, encoding="utf-8")


def _run(monkeypatch: pytest.MonkeyPatch, root: Path) -> int:
    monkeypatch.chdir(root)  # so check_misplaced_skills.Path.cwd() finds the skills dir
    monkeypatch.setattr(config, "REPO_ROOT", root)  # so config reads root/pyproject.toml
    return main()


def test_noop_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skills = tmp_path / ".agents" / "skills"
    _make_skill(skills, "coding-otel-a2a-relay")
    # No [tool.agentic-os.misplaced-skills] -> opt-in, passes.
    _write_pyproject(tmp_path, "[project]\nname = 'x'\n")
    assert _run(monkeypatch, tmp_path) == 0


def test_fails_on_denied_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    skills = tmp_path / ".agents" / "skills"
    _make_skill(skills, "coding-otel-a2a-relay")
    _make_skill(skills, "repo-agentic-os-kai")
    _write_pyproject(
        tmp_path,
        "[tool.agentic-os.misplaced-skills]\n"
        'deny = ["coding-*", "repo-*"]\n'
        'allow = ["repo-agentic-os-kai"]\n',
    )
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, tmp_path)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "coding-otel-a2a-relay" in err
    assert "repo-agentic-os-kai" not in err  # allow-listed


def test_passes_when_only_allowed_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills = tmp_path / ".agents" / "skills"
    _make_skill(skills, "repo-agentic-os-kai")
    _make_skill(skills, "kai-career")
    _write_pyproject(
        tmp_path,
        "[tool.agentic-os.misplaced-skills]\n"
        'deny = ["coding-*", "repo-*"]\n'
        'allow = ["repo-agentic-os-kai"]\n',
    )
    assert _run(monkeypatch, tmp_path) == 0


def test_disabled_flag_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills = tmp_path / ".agents" / "skills"
    _make_skill(skills, "coding-otel-a2a-relay")
    _write_pyproject(
        tmp_path,
        "[tool.agentic-os.misplaced-skills]\n"
        "enabled = false\n"
        'deny = ["coding-*"]\n',
    )
    assert _run(monkeypatch, tmp_path) == 0

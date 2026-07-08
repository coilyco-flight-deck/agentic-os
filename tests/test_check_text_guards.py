"""Tests for the staged text hygiene guards."""
from __future__ import annotations

import subprocess
from pathlib import Path

import agentic_os.config as cfg
from agentic_os.pre_commit import text_scan
from agentic_os.pre_commit import check_issue_references as ir
from agentic_os.pre_commit import check_unresolved_placeholders as up


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    return tmp_path


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_placeholder_guard_flags_unfinished_prose(monkeypatch, tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    _write(repo, "pyproject.toml", """
[tool.agentic-os.unresolved-placeholder-guard]
enabled = true
""")
    _write(repo, "docs/todo.md", "TODO implement the rest\n")
    _git(repo, "add", "-A")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cfg, "REPO_ROOT", repo, raising=True)
    monkeypatch.setattr(text_scan, "REPO_ROOT", repo, raising=True)
    assert up.main([]) == 1
    err = capsys.readouterr().err
    assert "todo-implement" in err


def test_placeholder_guard_honors_allowlist(monkeypatch, tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo, "pyproject.toml", """
[tool.agentic-os.unresolved-placeholder-guard]
enabled = true
allow_globs = ["docs/examples/**"]
""")
    _write(repo, "docs/examples/example.md", "placeholder text\n")
    _git(repo, "add", "-A")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cfg, "REPO_ROOT", repo, raising=True)
    monkeypatch.setattr(text_scan, "REPO_ROOT", repo, raising=True)
    assert up.main([]) == 0


def test_issue_guard_flags_direct_refs(monkeypatch, tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    _write(repo, "pyproject.toml", """
[tool.agentic-os.issue-reference-guard]
enabled = true
""")
    _write(repo, "README.md", "See #337 for the draft\n")
    _git(repo, "add", "-A")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cfg, "REPO_ROOT", repo, raising=True)
    monkeypatch.setattr(text_scan, "REPO_ROOT", repo, raising=True)
    assert ir.main([]) == 1
    err = capsys.readouterr().err
    assert "bare-issue-ref" in err


def test_issue_guard_honors_allowlist(monkeypatch, tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo, "pyproject.toml", """
[tool.agentic-os.issue-reference-guard]
enabled = true
allow_globs = ["docs/examples/**"]
""")
    _write(repo, "docs/examples/example.md", "See #337 for the draft\n")
    _git(repo, "add", "-A")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cfg, "REPO_ROOT", repo, raising=True)
    monkeypatch.setattr(text_scan, "REPO_ROOT", repo, raising=True)
    assert ir.main([]) == 0

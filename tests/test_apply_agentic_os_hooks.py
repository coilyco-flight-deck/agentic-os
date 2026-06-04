"""Tests for scripts/apply-agentic-os-hooks.py repo resolution.

Regression cover for agentic-os#102: the workspace root must be driven by
$PROJECTS_ROOT, not a hardcoded ~/projects/coilysiren. On Windows the default
home/projects path is wrong (the workspace lives on another drive, e.g.
X:/projects-x), so a `--repo <name>` run there reported "not checked out
locally" and a full run skipped every repo. Setting PROJECTS_ROOT must fix it
end to end through the script's own main(), not just the config helpers.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "apply-agentic-os-hooks.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("apply_agentic_os_hooks", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_repo(path: Path) -> None:
    (path / ".git").mkdir(parents=True)
    (path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")


def test_repo_found_via_projects_root_env(monkeypatch, tmp_path: Path) -> None:
    # Simulate the Windows case: workspace on a non-default root, not ~/projects.
    _make_repo(tmp_path / "coilysiren" / "atmosphere")
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path))
    script = _load_script()
    assert script.main(["--repo", "atmosphere", "--dry-run"]) == 0


def test_repo_missing_without_env_override(monkeypatch, tmp_path: Path) -> None:
    # Same workspace, but PROJECTS_ROOT points elsewhere: the repo is unreachable,
    # which is exactly the failure the hardcoded root produced on Windows.
    _make_repo(tmp_path / "workspace" / "coilysiren" / "atmosphere")
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    script = _load_script()
    assert script.main(["--repo", "atmosphere", "--dry-run"]) == 1


def test_full_run_spans_env_root(monkeypatch, tmp_path: Path, capsys) -> None:
    _make_repo(tmp_path / "coilyco-flight-deck" / "atmosphere")
    _make_repo(tmp_path / "coilysiren" / "warp")
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path))
    script = _load_script()
    assert script.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "atmosphere" in out
    assert "warp" in out

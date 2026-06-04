"""Tests for agentic_os.check_merge_conflicts: conflict-marker guard."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agentic_os import check_merge_conflicts as mc
from agentic_os import config

# Built at runtime so no source line in this file starts with a real marker
# (the hook would otherwise flag its own test).
OPEN = "<" * 7 + " HEAD"
SEP = "=" * 7
BASE = "|" * 7 + " base"
CLOSE = ">" * 7 + " branch"
CONFLICT = f"{OPEN}\nours\n{SEP}\ntheirs\n{CLOSE}\n"


def test_scan_flags_each_marker() -> None:
    hits = mc.scan("f.sh", CONFLICT)
    assert [h.split(":")[1] for h in hits] == ["1", "3", "5"]


def test_scan_flags_diff3_base() -> None:
    text = f"{OPEN}\nours\n{BASE}\nbase\n{SEP}\ntheirs\n{CLOSE}\n"
    assert len(mc.scan("f.sh", text)) == 4


def test_scan_clean_file() -> None:
    assert mc.scan("f.sh", "title\n===\nunderline not a separator\n") == []


def test_scan_separator_needs_exact_seven() -> None:
    # Six or eight equals are not a conflict separator.
    assert mc.scan("f.md", "======\n========\n") == []


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    return tmp_path


def _run(monkeypatch: pytest.MonkeyPatch, root: Path) -> int:
    monkeypatch.chdir(root)
    monkeypatch.setattr(mc, "REPO_ROOT", root)
    monkeypatch.setattr(config, "REPO_ROOT", root)
    return mc.main()


def test_staged_conflict_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    (root / "lockdown.sh").write_text(CONFLICT, encoding="utf-8")
    _git(root, "add", "lockdown.sh")
    assert _run(monkeypatch, root) == 1


def test_staged_clean_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    (root / "ok.sh").write_text("echo hi\n", encoding="utf-8")
    _git(root, "add", "ok.sh")
    assert _run(monkeypatch, root) == 0


def test_unstaged_conflict_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A conflicted file present but NOT staged does not block the commit:
    # the hook scans the index blobs when anything is staged.
    root = _repo(tmp_path)
    (root / "staged.sh").write_text("echo hi\n", encoding="utf-8")
    _git(root, "add", "staged.sh")
    (root / "dirty.sh").write_text(CONFLICT, encoding="utf-8")
    assert _run(monkeypatch, root) == 0


def test_all_files_fallback_scans_tracked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Nothing staged (committed, clean index): the `--all-files` fallback
    # scans tracked working-tree files and still catches the marker.
    root = _repo(tmp_path)
    (root / "bad.sh").write_text(CONFLICT, encoding="utf-8")
    _git(root, "add", "bad.sh")
    _git(root, "commit", "-m", "seed", "--no-verify")
    assert _run(monkeypatch, root) == 1


def test_exclude_opts_path_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    (root / "pyproject.toml").write_text(
        "[tool.agentic-os.merge-conflicts]\nexcludes = ['fixtures/*']\n",
        encoding="utf-8",
    )
    (root / "fixtures").mkdir()
    (root / "fixtures" / "sample.txt").write_text(CONFLICT, encoding="utf-8")
    _git(root, "add", "-A")
    assert _run(monkeypatch, root) == 0


def test_disabled_by_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    (root / "pyproject.toml").write_text(
        "[tool.agentic-os.merge-conflicts]\nenabled = false\n",
        encoding="utf-8",
    )
    (root / "bad.sh").write_text(CONFLICT, encoding="utf-8")
    _git(root, "add", "-A")
    assert _run(monkeypatch, root) == 0

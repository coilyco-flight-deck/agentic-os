"""Tests for scripts/apply-shell-links.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "apply-shell-links.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("apply_shell_links", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_repo(root: Path) -> None:
    (root / "shell").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "shell" / "zshrc").write_text("zsh\n", encoding="utf-8")
    (root / "shell" / "bashrc").write_text("bash\n", encoding="utf-8")
    (root / "scripts" / "gpg-ssm").write_text("gpg\n", encoding="utf-8")


def test_repoints_stale_symlink(tmp_path: Path) -> None:
    script = _load_script()
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    home.mkdir()
    _make_repo(repo)

    stale = repo / "zsh" / "zshrc"
    (repo / "zsh").mkdir()
    stale.write_text("old\n", encoding="utf-8")
    (home / ".zshrc").symlink_to(stale)

    spec = script.LinkSpec("zshrc", repo / "shell" / "zshrc", home / ".zshrc")
    action, _ = script.apply_link(spec, dry_run=False)

    assert action == "repointed"
    assert (home / ".zshrc").readlink() == repo / "shell" / "zshrc"


def test_backs_up_regular_file_before_linking(tmp_path: Path) -> None:
    script = _load_script()
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    home.mkdir()
    _make_repo(repo)
    (home / ".bashrc").write_text("custom\n", encoding="utf-8")

    spec = script.LinkSpec("bashrc", repo / "shell" / "bashrc", home / ".bashrc")
    action, _ = script.apply_link(spec, dry_run=False)

    assert action == "backed-up"
    assert (home / ".bashrc").is_symlink()
    assert (home / ".bashrc").readlink() == repo / "shell" / "bashrc"
    assert (home / ".bashrc.bak").read_text(encoding="utf-8") == "custom\n"


def test_check_reports_drift(tmp_path: Path) -> None:
    script = _load_script()
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    home.mkdir()
    _make_repo(repo)
    specs = script.link_specs(home, repo)

    action, _ = script.apply_link(specs[0], dry_run=True)

    assert action == "would-link"

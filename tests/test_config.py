"""Tests for agentic_os.config: per-repo exclude and enabled flags."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os.config import (
    get_int_option,
    is_enabled,
    is_excluded,
    iter_workspace_repos,
    load_excludes,
    projects_root,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return tmp_path


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------- load_excludes ----------

def test_no_config_returns_empty(repo: Path) -> None:
    assert load_excludes("documentation-layout", repo) == []


def test_pyproject_excludes(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
excludes = ["src/pages/", "**/generated/*.md"]
""")
    assert load_excludes("documentation-layout", repo) == [
        "src/pages/",
        "**/generated/*.md",
    ]


def test_agentic_os_toml_excludes(repo: Path) -> None:
    write(repo / ".agentic-os.toml", """
[documentation-layout]
excludes = ["src/pages/**"]
""")
    assert load_excludes("documentation-layout", repo) == ["src/pages/**"]


def test_pyproject_wins_over_agentic_os_toml(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
excludes = ["from-pyproject/"]
""")
    write(repo / ".agentic-os.toml", """
[documentation-layout]
excludes = ["from-toml/"]
""")
    assert load_excludes("documentation-layout", repo) == ["from-pyproject/"]


def test_other_hook_unaffected(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
excludes = ["src/pages/"]
""")
    assert load_excludes("code-comments", repo) == []


def test_malformed_excludes_returns_empty(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
excludes = "not-a-list"
""")
    assert load_excludes("documentation-layout", repo) == []


def test_malformed_toml_returns_empty(repo: Path) -> None:
    write(repo / "pyproject.toml", "this is not valid toml = {{{")
    assert load_excludes("documentation-layout", repo) == []


# ---------- is_enabled ----------

def test_enabled_default_true(repo: Path) -> None:
    assert is_enabled("documentation-layout", repo) is True


def test_enabled_false(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.catalog-trifecta]
enabled = false
""")
    assert is_enabled("catalog-trifecta", repo) is False


def test_enabled_explicit_true(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
enabled = true
""")
    assert is_enabled("documentation-layout", repo) is True


def test_enabled_via_agentic_os_toml(repo: Path) -> None:
    write(repo / ".agentic-os.toml", """
[catalog-trifecta]
enabled = false
""")
    assert is_enabled("catalog-trifecta", repo) is False


# ---------- get_int_option ----------

def test_int_option_default_when_unset(repo: Path) -> None:
    assert get_int_option("documentation-layout", "agents_md_max_chars", 4000, repo) == 4000


def test_int_option_reads_pyproject(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
agents_md_max_lines = 160
agents_md_max_chars = 12000
""")
    assert get_int_option("documentation-layout", "agents_md_max_lines", 80, repo) == 160
    assert get_int_option("documentation-layout", "agents_md_max_chars", 4000, repo) == 12000


def test_int_option_rejects_non_int(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
agents_md_max_chars = "lots"
""")
    assert get_int_option("documentation-layout", "agents_md_max_chars", 4000, repo) == 4000


def test_int_option_rejects_bool(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
agents_md_max_chars = true
""")
    assert get_int_option("documentation-layout", "agents_md_max_chars", 4000, repo) == 4000


def test_int_option_scoped_to_hook(repo: Path) -> None:
    write(repo / "pyproject.toml", """
[tool.agentic-os.documentation-layout]
agents_md_max_chars = 12000
""")
    assert get_int_option("code-comments", "agents_md_max_chars", 4000, repo) == 4000


# ---------- is_excluded ----------

@pytest.mark.parametrize("path, patterns, expected", [
    ("src/pages/foo.md", ["src/pages/"], True),
    ("src/pages/posts/bar.md", ["src/pages/"], True),
    ("src/components/foo.tsx", ["src/pages/"], False),
    ("src/pages/foo.md", ["src/pages/**"], True),
    ("src/pages", ["src/pages/**"], True),
    ("other.md", ["src/pages/**"], False),
    ("docs/foo.md", ["docs/*.md"], True),
    ("docs/sub/foo.md", ["docs/*.md"], False),
    ("README.md", ["*.md"], True),
    ("nested/README.md", ["*.md"], False),
    ("a/b/c.md", ["**/c.md"], True),
])
def test_is_excluded(path: str, patterns: list[str], expected: bool) -> None:
    assert is_excluded(path, patterns) is expected


def test_is_excluded_empty_patterns() -> None:
    assert is_excluded("anything.md", []) is False


# ---------- projects_root ----------

def test_projects_root_explicit_wins(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROJECTS_ROOT", "/should/be/ignored")
    assert projects_root(tmp_path) == tmp_path


def test_projects_root_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path))
    assert projects_root() == tmp_path


def test_projects_root_default(monkeypatch) -> None:
    monkeypatch.delenv("PROJECTS_ROOT", raising=False)
    assert projects_root() == Path.home() / "projects"


# ---------- iter_workspace_repos ----------

def _make_repo(path: Path) -> None:
    (path / ".git").mkdir(parents=True)


def test_iter_workspace_repos_spans_org_dirs(tmp_path: Path) -> None:
    # ~/projects layout: org dirs holding repos, no .git on the org dirs.
    _make_repo(tmp_path / "coilysiren" / "repo-a")
    _make_repo(tmp_path / "coilyco-bridge" / "repo-b")
    _make_repo(tmp_path / "coilyco-flight-deck" / "repo-c")
    repos = iter_workspace_repos(tmp_path)
    # Sorted by (org dir, repo name): bridge, flight-deck, coilysiren.
    assert [r.name for r in repos] == ["repo-b", "repo-c", "repo-a"]
    assert (tmp_path / "coilyco-bridge" / "repo-b") in repos


def test_iter_workspace_repos_single_org_root(tmp_path: Path) -> None:
    # $PROJECTS_ROOT pointed straight at one org dir: children carry .git.
    _make_repo(tmp_path / "repo-a")
    _make_repo(tmp_path / "repo-b")
    repos = iter_workspace_repos(tmp_path)
    assert [r.name for r in repos] == ["repo-a", "repo-b"]


def test_iter_workspace_repos_skips_hidden(tmp_path: Path) -> None:
    _make_repo(tmp_path / "coilysiren" / "repo-a")
    # .dispatch-worktrees scaffolding under an org dir, and a hidden org dir.
    _make_repo(tmp_path / "coilysiren" / ".dispatch-worktrees" / "wt")
    _make_repo(tmp_path / ".hidden-org" / "repo-x")
    repos = iter_workspace_repos(tmp_path)
    assert [r.name for r in repos] == ["repo-a"]


def test_iter_workspace_repos_skips_non_git_dirs(tmp_path: Path) -> None:
    _make_repo(tmp_path / "coilysiren" / "repo-a")
    (tmp_path / "coilysiren" / "not-a-repo").mkdir(parents=True)
    repos = iter_workspace_repos(tmp_path)
    assert [r.name for r in repos] == ["repo-a"]


def test_iter_workspace_repos_missing_root(tmp_path: Path) -> None:
    assert iter_workspace_repos(tmp_path / "nope") == []


def test_iter_workspace_repos_honors_env(monkeypatch, tmp_path: Path) -> None:
    _make_repo(tmp_path / "coilysiren" / "repo-a")
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path))
    repos = iter_workspace_repos()
    assert [r.name for r in repos] == ["repo-a"]

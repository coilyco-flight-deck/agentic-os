"""Tests for agentic_os.config: per-repo exclude and enabled flags."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os.config import (
    get_int_option,
    is_enabled,
    is_excluded,
    load_excludes,
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

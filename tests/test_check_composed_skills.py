from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agentic_os import config
from agentic_os.pre_commit.check_composed_skills import (
    catalogue_problems,
    layout_problems,
    role_selectors,
)


def write(path: Path, body: str = "# Source\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_composed_layout_accepts_distinct_composed_entrypoints(tmp_path: Path) -> None:
    write(tmp_path / ".agents" / "skills" / "categories.yaml")
    write(tmp_path / ".agents" / "skills" / "coding-go" / "SKILL.md")
    write(tmp_path / ".agents" / "composed" / "coding-shape-cli" / "COMPOSED.md")

    assert layout_problems(tmp_path) == []


def test_composed_layout_rejects_discoverable_and_colliding_sources(
    tmp_path: Path,
) -> None:
    write(tmp_path / ".agents" / "skills" / "categories.yaml")
    write(tmp_path / ".agents" / "skills" / "coding-go" / "SKILL.md")
    write(tmp_path / ".agents" / "composed" / "coding-go" / "COMPOSED.md")
    write(tmp_path / ".agents" / "composed" / "coding-go" / "nested" / "SKILL.md")
    (tmp_path / ".agents" / "composed" / "missing").mkdir(parents=True)

    problems = layout_problems(tmp_path)

    assert any("must use COMPOSED.md" in problem for problem in problems)
    assert any("collides with" in problem for problem in problems)
    assert any("missing COMPOSED.md" in problem for problem in problems)


def test_composed_layout_requires_the_ordinary_taxonomy(tmp_path: Path) -> None:
    write(tmp_path / ".agents" / "composed" / "design-system" / "COMPOSED.md")

    assert layout_problems(tmp_path) == [
        ".agents/composed: role-composed sources require "
        ".agents/skills/categories.yaml"
    ]


# Deleting the parked `role exec` block left the Executive Strategist composing
# zero methods for eleven days, unnoticed. agentic-os#1073


def _catalogue(tmp_path: Path, kdl: str | None, names: list[str]) -> Path:
    composed = tmp_path / ".agents" / "composed"
    for name in names:
        (composed / name).mkdir(parents=True, exist_ok=True)
        (composed / name / "COMPOSED.md").write_text("", encoding="utf-8")
    composed.mkdir(parents=True, exist_ok=True)
    if kdl is not None:
        (tmp_path / ".agents" / "roles.kdl").write_text(kdl, encoding="utf-8")
    return composed


def test_a_role_with_no_selector_fails(tmp_path: Path) -> None:
    kdl = "roles {\n    role exec {\n    }\n\n    role qa {\n        composed-skill a\n    }\n}\n"
    composed = _catalogue(tmp_path, kdl, ["a"])

    problems = catalogue_problems(tmp_path, composed)

    assert len(problems) == 1
    assert "role exec has no composed-skill selector" in problems[0]


def test_an_unselected_source_fails(tmp_path: Path) -> None:
    kdl = "roles {\n    role qa {\n        composed-skill a\n    }\n}\n"
    composed = _catalogue(tmp_path, kdl, ["a", "orphan"])

    problems = catalogue_problems(tmp_path, composed)

    assert len(problems) == 1
    assert "orphan: no role selects it" in problems[0]


def test_a_glob_selector_claims_its_sources(tmp_path: Path) -> None:
    # The control. Most selectors are globs, so a literal-only match would
    # report the whole catalogue as orphaned.
    kdl = 'roles {\n    role qa {\n        composed-skill "coding-*"\n    }\n}\n'
    composed = _catalogue(tmp_path, kdl, ["coding-go", "coding-rust"])

    assert catalogue_problems(tmp_path, composed) == []


def test_a_repo_with_no_role_graph_is_left_alone(tmp_path: Path) -> None:
    # The hook ships to consumers that carry composed sources and no roles.kdl.
    composed = _catalogue(tmp_path, None, ["a"])

    assert role_selectors(tmp_path) is None
    assert catalogue_problems(tmp_path, composed) == []


def test_this_repos_catalogue_and_role_graph_agree() -> None:
    # The live pairing, through the opt-out list rather than around it.
    root = Path(__file__).resolve().parent.parent

    assert catalogue_problems(root, root / ".agents" / "composed") == []


def _with_unselected(tmp_path: Path, patterns: list[str]) -> None:
    body = ", ".join(f'"{p}"' for p in patterns)
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.agentic-os.check-composed-skills]\nunselected = [{body}]\n",
        encoding="utf-8",
    )


def test_a_live_exemption_still_passes(tmp_path: Path) -> None:
    # The control. A pattern covering a genuinely unselected source is the
    # whole point of the escape hatch and must stay silent.
    kdl = "roles {\n    role qa {\n        composed-skill a\n    }\n}\n"
    composed = _catalogue(tmp_path, kdl, ["a", "orphan"])
    _with_unselected(tmp_path, ["orphan"])

    assert catalogue_problems(tmp_path, composed) == []


def test_an_exemption_whose_source_is_gone_fails(tmp_path: Path) -> None:
    kdl = "roles {\n    role qa {\n        composed-skill a\n    }\n}\n"
    composed = _catalogue(tmp_path, kdl, ["a"])
    _with_unselected(tmp_path, ["deleted-long-ago"])

    problems = catalogue_problems(tmp_path, composed)

    assert len(problems) == 1
    assert "'deleted-long-ago' covers no unselected source" in problems[0]


def test_an_exemption_a_role_now_selects_fails(tmp_path: Path) -> None:
    # The dangerous drift: the exemption is wrong and still active, so removing
    # the selector later would leave the gate silent.
    kdl = "roles {\n    role qa {\n        composed-skill a\n        composed-skill b\n    }\n}\n"
    composed = _catalogue(tmp_path, kdl, ["a", "b"])
    _with_unselected(tmp_path, ["b"])

    problems = catalogue_problems(tmp_path, composed)

    assert len(problems) == 1
    assert "'b' covers no unselected source" in problems[0]


def test_a_selector_matching_nothing_fails(tmp_path: Path) -> None:
    # #1205: the role has a selector and every source is claimed, so neither
    # existing direction fires while the role composes less than it says.
    kdl = "roles {\n    role qa {\n        composed-skill a\n        composed-skill coding-rust\n    }\n}\n"
    composed = _catalogue(tmp_path, kdl, ["a"])

    problems = catalogue_problems(tmp_path, composed)

    assert len(problems) == 1
    assert "selects 'coding-rust'" in problems[0]


def test_a_glob_selector_matching_one_source_passes(tmp_path: Path) -> None:
    kdl = "roles {\n    role qa {\n        composed-skill tooling-*\n    }\n}\n"
    composed = _catalogue(tmp_path, kdl, ["tooling-x"])

    assert catalogue_problems(tmp_path, composed) == []


# These need a real checkout. The layout tests above pass under tmp_path only
# because git cannot answer there, which is why the shell went unseen. #7702


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _composed_checkout(root: Path, ignore: str | None = None) -> None:
    """A committed catalogue with one populated source, as the fleet ships it."""
    _git(root, "init", "-q")
    write(root / "README.md", "# Repo\n")
    write(root / ".agents" / "skills" / "categories.yaml")
    write(root / ".agents" / "composed" / "tooling-kept" / "COMPOSED.md")
    if ignore is not None:
        write(root / ".gitignore", f"{ignore}\n")
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed")


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    config.reset_build_output_cache()


def test_a_populated_source_passes_on_a_real_checkout(tmp_path: Path) -> None:
    # The negative control. A hook of this kind that passes everything is the
    # defect being fixed, so the pass has to be asserted beside the failure.
    _composed_checkout(tmp_path)

    assert layout_problems(tmp_path) == []


def test_an_empty_shell_directory_fails(tmp_path: Path) -> None:
    _composed_checkout(tmp_path)
    (tmp_path / ".agents" / "composed" / "tooling-moved-away").mkdir()

    problems = layout_problems(tmp_path)

    assert len(problems) == 1
    assert ".agents/composed/tooling-moved-away" in problems[0]
    assert "empty directory" in problems[0]
    assert "git mv" in problems[0]


def test_a_shell_holding_only_an_empty_subdirectory_fails(tmp_path: Path) -> None:
    # The originally reported shape: `git mv` emptied references/ and `git rm`
    # took COMPOSED.md, leaving two nested directories and no file.
    _composed_checkout(tmp_path)
    (tmp_path / ".agents" / "composed" / "tooling-folded" / "references").mkdir(
        parents=True
    )

    problems = layout_problems(tmp_path)

    assert len(problems) == 1
    assert ".agents/composed/tooling-folded" in problems[0]


def test_a_gitignored_bake_is_still_skipped(tmp_path: Path) -> None:
    # The other negative control. A baked tree git does not carry still has to
    # pass, or this fix re-opens sirens-echo#800 from the other side.
    _composed_checkout(tmp_path, ignore=".agents/composed/baked/")
    write(tmp_path / ".agents" / "composed" / "baked" / "notes.md", "# Baked\n")

    assert layout_problems(tmp_path) == []


def test_the_shell_check_is_what_git_status_cannot_show(tmp_path: Path) -> None:
    # The whole reason the hook has to carry this: git reports a clean tree.
    _composed_checkout(tmp_path)
    (tmp_path / ".agents" / "composed" / "tooling-moved-away").mkdir()

    shown = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert shown == ""
    assert layout_problems(tmp_path) != []

"""Tests for agentic_os.check_seed_skills: per-repo seed-reference guard."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os import check_seed_skills as csk
from agentic_os import config

# A fixed table so tests do not depend on the shipped seed_skills_data.py.
ALWAYS = ["coding-git"]
LANGUAGES = {
    "python": {"skill": "coding-python", "extensions": [".py", ".pyi"]},
    "go": {"skill": "coding-go", "extensions": [".go"]},
}


def test_detect_languages_by_extension() -> None:
    paths = ["src/app.py", "main.go", "README.md", "notes.txt"]
    assert csk.detect_languages(paths, LANGUAGES) == {"python", "go"}


def test_detect_languages_none() -> None:
    assert csk.detect_languages(["README.md", "x.rs"], LANGUAGES) == set()


def test_required_skills_always_plus_languages_deduped() -> None:
    req = csk.required_skills({"python"}, ALWAYS, LANGUAGES)
    assert req == ["coding-git", "coding-python"]


def test_referenced_skills_matches_canonical_path() -> None:
    doc = "see .agents/skills/coding-python/SKILL.md for details"
    assert csk.referenced_skills([doc], ["coding-python", "coding-git"]) == {
        "coding-python"
    }


def _setup(monkeypatch: pytest.MonkeyPatch, root: Path, pyproject: str) -> None:
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    monkeypatch.chdir(root)
    monkeypatch.setattr(config, "REPO_ROOT", root)
    monkeypatch.setattr(csk, "load_data", lambda: (ALWAYS, dict(LANGUAGES)))


def test_noop_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    _setup(monkeypatch, tmp_path, "[project]\nname = 'x'\n")
    assert csk.main() == 0  # opt-in: no section, no enforcement


def test_fails_when_code_unreferenced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# repo\n", encoding="utf-8")
    _setup(monkeypatch, tmp_path, "[tool.agentic-os.seed-skills]\nenabled = true\n")
    with pytest.raises(SystemExit) as exc:
        csk.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "coding-python" in err  # language-gated
    assert "coding-git" in err  # always baseline


def test_passes_when_referenced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "context:\n"
        "- .agents/skills/coding-git/SKILL.md\n"
        "- .agents/skills/coding-python/SKILL.md\n",
        encoding="utf-8",
    )
    _setup(monkeypatch, tmp_path, "[tool.agentic-os.seed-skills]\nenabled = true\n")
    assert csk.main() == 0


def test_no_code_only_needs_always(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A docs-only repo still owes the always-on baseline reference.
    (tmp_path / "AGENTS.md").write_text(
        "ctx: .agents/skills/coding-git/SKILL.md\n", encoding="utf-8"
    )
    _setup(monkeypatch, tmp_path, "[tool.agentic-os.seed-skills]\nenabled = true\n")
    assert csk.main() == 0


def test_disabled_flag_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    _setup(
        monkeypatch,
        tmp_path,
        "[tool.agentic-os.seed-skills]\nenabled = false\n",
    )
    assert csk.main() == 0


def test_excludes_skip_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The only Python lives under an excluded path, so python is not detected;
    # the always baseline is referenced, so the repo passes.
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "dep.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "ctx: .agents/skills/coding-git/SKILL.md\n", encoding="utf-8"
    )
    _setup(
        monkeypatch,
        tmp_path,
        "[tool.agentic-os.seed-skills]\nenabled = true\nexcludes = ['vendor/']\n",
    )
    assert csk.main() == 0

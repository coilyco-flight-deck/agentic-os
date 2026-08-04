"""Tests for agentic_os.generators.generate_seed_skills: frontmatter scan, generate, drift."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os.generators import generate_seed_skills as seed_skills


def _make_skill(composed_dir: Path, name: str, seed_block: str | None) -> None:
    d = composed_dir / name
    d.mkdir(parents=True)
    fm = f"name: {name}\ndescription: x\n"
    if seed_block is not None:
        fm += seed_block
    (d / "COMPOSED.md").write_text(
        f"---\n{fm}---\n\n# {name}\n", encoding="utf-8"
    )


def test_iter_collects_always_and_languages(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    _make_skill(composed, "coding-core-git", "seed:\n  kind: always\n")
    _make_skill(
        composed,
        "coding-python",
        "seed:\n  kind: language\n  language: python\n  extensions: [.py, .pyi]\n",
    )
    _make_skill(composed, "coding-plain", None)  # no seed: ignored
    always, languages = seed_skills.iter_seed_skills(composed)
    assert always == ["coding-core-git"]
    assert languages == {
        "python": {"skill": "coding-python", "extensions": [".py", ".pyi"]}
    }


def test_iter_rejects_bad_kind(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    _make_skill(composed, "coding-x", "seed:\n  kind: nonsense\n")
    with pytest.raises(ValueError, match="seed.kind"):
        seed_skills.iter_seed_skills(composed)


def test_iter_rejects_language_without_extensions(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    _make_skill(composed, "coding-x", "seed:\n  kind: language\n  language: x\n")
    with pytest.raises(ValueError, match="extensions"):
        seed_skills.iter_seed_skills(composed)


def test_iter_rejects_duplicate_language(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    _make_skill(
        composed, "coding-a",
        "seed:\n  kind: language\n  language: py\n  extensions: [.a]\n",
    )
    _make_skill(
        composed, "coding-b",
        "seed:\n  kind: language\n  language: py\n  extensions: [.b]\n",
    )
    with pytest.raises(ValueError, match="claimed by both"):
        seed_skills.iter_seed_skills(composed)


def test_iter_rejects_duplicate_extension(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    _make_skill(
        composed, "coding-a",
        "seed:\n  kind: language\n  language: a\n  extensions: [.x]\n",
    )
    _make_skill(
        composed, "coding-b",
        "seed:\n  kind: language\n  language: b\n  extensions: [.x]\n",
    )
    with pytest.raises(ValueError, match="extension '.x'"):
        seed_skills.iter_seed_skills(composed)


def test_render_is_importable_and_roundtrips() -> None:
    always = ["coding-core-git"]
    languages = {"python": {"skill": "coding-python", "extensions": [".py"]}}
    src = seed_skills.render_data_module(always, languages)
    ns: dict = {}
    exec(compile(src, "seed_skills_data.py", "exec"), ns)  # noqa: S102 - generated
    assert ns["SEED_ALWAYS"] == always
    assert ns["SEED_LANGUAGES"] == languages


def test_generate_then_check_drift_passes(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    _make_skill(composed, "coding-core-git", "seed:\n  kind: always\n")
    data_path = tmp_path / "seed_skills_data.py"
    assert seed_skills.generate(composed, data_path) == 0
    assert seed_skills.check_drift(composed, data_path) == 0


def test_check_drift_fails_when_stale(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    _make_skill(composed, "coding-core-git", "seed:\n  kind: always\n")
    data_path = tmp_path / "seed_skills_data.py"
    data_path.write_text("SEED_ALWAYS = []\nSEED_LANGUAGES = {}\n", encoding="utf-8")
    assert seed_skills.check_drift(composed, data_path) == 1


def test_source_ref_points_to_composed_entrypoint() -> None:
    assert (
        seed_skills.source_ref("coding-python")
        == ".agents/composed/coding-python/COMPOSED.md"
    )
    assert seed_skills.suggested_url("coding-python").endswith(
        "/.agents/composed/coding-python/COMPOSED.md"
    )

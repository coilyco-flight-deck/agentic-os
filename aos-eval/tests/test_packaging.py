"""The package's own shipping contract, which a consumer discovers too late."""

from __future__ import annotations

import tomllib
from pathlib import Path

import aos_eval

ROOT = Path(__file__).resolve().parents[1]


def test_the_typing_marker_ships():
    """Without it a strict-mypy consumer reads every import here as untyped."""
    installed = Path(str(aos_eval.__file__)).parent
    assert (installed / "py.typed").is_file()


def test_the_marker_is_declared_as_package_data():
    """Present in the tree is not the same as present in the built wheel."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    declared = config["tool"]["setuptools"]["package-data"]["aos_eval"]
    assert "py.typed" in declared


def test_no_runner_reaches_the_dependency_set():
    """The whole reason this is a second package. See docs/release.md."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    names = " ".join(config["project"]["dependencies"]).lower()
    for runner in ("inspect-ai", "openai", "anthropic", "litellm"):
        assert runner not in names

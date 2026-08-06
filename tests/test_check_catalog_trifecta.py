"""Tests for the self-contained catalog-trifecta contract."""
from __future__ import annotations

from pathlib import Path

import agentic_os.config as config
from agentic_os.pre_commit import check_catalog_trifecta as trifecta


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def point_at(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(trifecta, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)


def agents_body() -> str:
    headings = [
        "Scope",
        "Project shape",
        "Repo boundaries",
        "Commands",
        "Validation",
        "Safety",
        "Cross-repo contracts",
        "Release",
        "Agent rules",
    ]
    body = "# Agent instructions\n\n"
    body += "\n\n".join(f"## {heading}\n\nCurrent contract." for heading in headings)
    return body + (
        "\n\n## See also\n\n"
        "* [README](README.md)\n"
        "* [Features](docs/FEATURES.md)\n"
        "* [Ward](.ward/ward.yaml)\n"
    )


def write_valid_consumer(tmp_path: Path) -> None:
    write(
        tmp_path / "README.md",
        "# Product\n\n## See also\n\n"
        "* [Agents](AGENTS.md)\n"
        "* [Features](docs/FEATURES.md)\n"
        "* [Ward](.ward/ward.yaml)\n",
    )
    write(tmp_path / "AGENTS.md", agents_body())
    write(
        tmp_path / "docs" / "FEATURES.md",
        "# Features\n\n## See also\n\n"
        "* [README](../README.md)\n"
        "* [Agents](../AGENTS.md)\n"
        "* [Ward](../.ward/ward.yaml)\n",
    )
    write(tmp_path / ".ward" / "ward.yaml", "commands: {}\n")


def test_consumer_crosslinks_without_aos_internal_citation(
    tmp_path: Path, monkeypatch
) -> None:
    point_at(tmp_path, monkeypatch)
    write_valid_consumer(tmp_path)

    assert trifecta.main() == 0
    assert not (tmp_path / "docs" / "features-release-tooling.md").exists()


def test_consumer_still_needs_every_peer_link(tmp_path: Path, monkeypatch) -> None:
    point_at(tmp_path, monkeypatch)
    write_valid_consumer(tmp_path)
    write(
        tmp_path / "README.md",
        "# Product\n\n## See also\n\n"
        "* [Agents](AGENTS.md)\n"
        "* [Features](docs/FEATURES.md)\n",
    )

    assert trifecta.main() == 1

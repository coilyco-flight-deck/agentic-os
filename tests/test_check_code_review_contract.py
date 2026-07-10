"""Tests for agentic_os.pre_commit.check_code_review_contract."""
from __future__ import annotations

from pathlib import Path

import agentic_os.config as config
from agentic_os.pre_commit import check_code_review_contract as crc


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _point_repo_root_at(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(crc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)


def test_missing_code_review_md_is_flagged(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _point_repo_root_at(tmp_path, monkeypatch)
    assert crc.main() == 1
    err = capsys.readouterr().err
    assert "CODE-REVIEW.md missing" in err


def test_localized_historical_contract_passes(
    tmp_path: Path, monkeypatch
) -> None:
    _point_repo_root_at(tmp_path, monkeypatch)
    write(
        tmp_path / "CODE-REVIEW.md",
        "# Code review contract\n"
        "\n"
        "## Localized invariants\n"
        "Review the smallest repo-local surface that can break.\n"
        "\n"
        "## Historical issues\n"
        "Defend against regressions that have already happened.\n"
        "\n"
        "## Update triggers\n"
        "Refresh this file when the issue re-occurs or a work stop appears.\n",
    )
    assert crc.check_code_review_contract() == []


def test_generic_only_content_is_rejected(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _point_repo_root_at(tmp_path, monkeypatch)
    write(
        tmp_path / "CODE-REVIEW.md",
        "# Review notes\n"
        "\n"
        "## General review rules\n"
        "Don't use 1-letter variable names.\n",
    )
    assert crc.main() == 1
    err = capsys.readouterr().err
    assert "required H2 section" in err
    assert "generic-purpose review advice" in err

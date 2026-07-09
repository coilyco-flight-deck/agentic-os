"""Tests for the dev-base image contract."""
from __future__ import annotations

from pathlib import Path


DOCKERFILE = Path(__file__).resolve().parent.parent / "docker" / "dev-base" / "Dockerfile"


def test_root_bootstrap_home_is_pinned_to_root() -> None:
    text = DOCKERFILE.read_text()
    assert "HOME=/root" in text

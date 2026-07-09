"""Tests for the dev-base image contract."""
from __future__ import annotations

from pathlib import Path


DOCKERFILE = Path(__file__).resolve().parent.parent / "docker" / "dev-base" / "Dockerfile"


def test_root_bootstrap_home_is_pinned_to_root() -> None:
    text = DOCKERFILE.read_text()
    assert "HOME=/root" in text
    assert "Acquire::Retries=3" in text
    assert "for attempt in 1 2 3" in text


def test_kubectl_smoke_check_uses_supported_client_only_flag() -> None:
    text = DOCKERFILE.read_text()
    assert "kubectl version --client --short" not in text
    assert "kubectl version --client=true" in text


def test_homebrew_is_installed_noninteractively() -> None:
    text = DOCKERFILE.read_text()
    assert "/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin" in text
    assert "USER linuxbrew" in text
    assert "NONINTERACTIVE=1" in text
    assert "brew --version" in text


def test_dev_base_docs_include_homebrew_tooling() -> None:
    text = (Path(__file__).resolve().parent.parent / "docs" / "dev-base-image.md").read_text()
    assert "**Homebrew**" in text

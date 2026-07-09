"""Tests for the dev-base image contract."""
from __future__ import annotations

import json
from pathlib import Path


DOCKERFILE = Path(__file__).resolve().parent.parent / "docker" / "dev-base" / "Dockerfile"
IMAGE_MANIFEST = Path(__file__).resolve().parent.parent / "docker" / "dev-base" / "ci-image-manifest.json"


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


def test_ward_is_pinned_and_smoke_checked() -> None:
    text = DOCKERFILE.read_text()
    assert "ARG WARD_VERSION=0.529.0" in text
    assert 'git clone --depth 1 --branch "v${WARD_VERSION}"' in text
    assert "ward --version" in text


def test_dev_base_exposes_named_targets_and_a_ward_builder() -> None:
    text = DOCKERFILE.read_text()
    assert "AS dev-base-core" in text
    assert "AS dev-base-lang-node" in text
    assert "AS dev-base-lang-go" in text
    assert "AS dev-base-lang-dotnet" in text
    assert "AS dev-base-ops" in text
    assert "AS dev-base-agent" in text
    assert "AS dev-base-full" in text
    assert "AS dev-base-ward-builder" in text
    assert 'COPY --from=dev-base-ward-builder /usr/local/bin/ward /usr/local/bin/ward' in text


def test_dev_base_docs_include_homebrew_tooling() -> None:
    text = (Path(__file__).resolve().parent.parent / "docs" / "dev-base-image.md").read_text()
    assert "**Homebrew**" in text


def test_dev_base_manifest_maps_every_image_class_to_the_same_tag() -> None:
    manifest = json.loads(IMAGE_MANIFEST.read_text())
    expected = {
        "dev-base-core",
        "dev-base-lang-node",
        "dev-base-lang-go",
        "dev-base-lang-dotnet",
        "dev-base-ops",
        "dev-base-agent",
        "dev-base-full",
    }
    assert set(manifest) == expected
    assert len({ref.rsplit(":", 1)[-1] for ref in manifest.values()}) == 1
    assert all(ref.startswith("forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:") for ref in manifest.values())

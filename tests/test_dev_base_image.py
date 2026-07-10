"""Tests for the dev-base image contract."""
from __future__ import annotations

from pathlib import Path

from agentic_os.dev_base import DEV_BASE_ROOT, REGISTRY_BASE, PUBLISHED_TIER_NAMES, publish_plan


def _tier_path(tier: str) -> Path:
    return DEV_BASE_ROOT / tier / "Dockerfile"


def test_dev_base_tier_directories_exist() -> None:
    for tier in PUBLISHED_TIER_NAMES:
        assert _tier_path(tier).is_file()


def test_dev_base_plan_is_derived_from_tier_folder_names() -> None:
    tag = "v0.242.0"
    plan = publish_plan(REGISTRY_BASE, tag)

    assert [entry["tier"] for entry in plan] == list(PUBLISHED_TIER_NAMES)
    assert [entry["image"] for entry in plan] == [
        f"{REGISTRY_BASE}-{tier}:{tag}" for tier in PUBLISHED_TIER_NAMES
    ]
    assert [entry["stage"] for entry in plan] == [
        f"dev-base-{tier}" for tier in PUBLISHED_TIER_NAMES
    ]
    assert [entry["dockerfile"] for entry in plan] == [
        f"docker/dev-base/{tier}/Dockerfile" for tier in PUBLISHED_TIER_NAMES
    ]
    assert [entry["base_image"] for entry in plan] == [
        "ubuntu:24.04",
        f"{REGISTRY_BASE}-core:{tag}",
        f"{REGISTRY_BASE}-lang-node:{tag}",
        f"{REGISTRY_BASE}-lang-go:{tag}",
        f"{REGISTRY_BASE}-lang-dotnet:{tag}",
        f"{REGISTRY_BASE}-ops:{tag}",
        f"{REGISTRY_BASE}-agent:{tag}",
    ]
    assert plan[-1]["tier"] == "full"


def test_core_tier_keeps_the_hidden_ward_builder_stage() -> None:
    text = _tier_path("core").read_text()
    assert "AS dev-base-ward-builder" in text
    assert 'COPY --from=dev-base-ward-builder /usr/local/bin/ward /usr/local/bin/ward' in text
    assert "ARG WARD_VERSION=0.529.0" in text


def test_tier_files_chain_from_the_previous_tier_image() -> None:
    for tier in ("lang-node", "lang-go", "lang-dotnet", "ops", "agent", "full"):
        text = _tier_path(tier).read_text()
        assert f"FROM ${{BASE_IMAGE}} AS dev-base-{tier}" in text
        assert "ARG BASE_IMAGE" in text


def test_agent_tier_still_copies_the_stable_assets_from_the_root_context() -> None:
    text = _tier_path("agent").read_text()
    assert "COPY agent-name.sh /opt/agentic-os/agent-name.sh" in text
    assert "COPY statusline.sh /opt/agentic-os/statusline.sh" in text
    assert "COPY statusline.d/ /opt/agentic-os/statusline.d/" in text
    assert "COPY claude-managed-settings.json /etc/claude-code/managed-settings.json" in text
    assert "COPY substrate-image-repos.txt /tmp/substrate-image-repos.txt" in text


def test_full_tier_remains_the_default_surface() -> None:
    text = _tier_path("full").read_text()
    assert "WORKDIR /workspace" in text
    assert 'CMD ["bash"]' in text


def test_old_manifest_is_gone() -> None:
    assert not (DEV_BASE_ROOT / "Dockerfile").exists()
    assert not (DEV_BASE_ROOT / "ci-image-manifest.json").exists()

"""Tests for the dev-base image contract."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from agentic_os.dev_base import (
    DEV_BASE_ROOT,
    REGISTRY_BASE,
    PUBLISHED_TIER_NAMES,
    cache_ref,
    publish_plan,
)

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dev-base-build.py"


def _tier_path(tier: str) -> Path:
    return DEV_BASE_ROOT / tier / "Dockerfile"


def _load_script():
    spec = importlib.util.spec_from_file_location("dev_base_build", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert "ARG WARD_VERSION=0.567.0" in text
    assert "ARG WARD_CONFIG_REF_COMMIT" in text
    assert "WARD_CONFIG_REF=forgejo.coilysiren.me/coilyco-flight-deck/agentic-os@${WARD_CONFIG_REF_COMMIT}//.ward" in text


def test_core_tier_runs_ward_doctor_after_installing_ward() -> None:
    text = _tier_path("core").read_text()
    assert (
        text.index('COPY --from=dev-base-ward-builder /usr/local/bin/ward /usr/local/bin/ward')
        < text.index("ward doctor")
    )
    assert "ward --version; \\\n    CLIGUARD_NO_SANDBOX=1 ward doctor; \\" in text


def test_shell_common_exports_a_commit_addressed_ward_config_ref() -> None:
    text = (Path(__file__).resolve().parent.parent / "shell" / "common.sh").read_text()
    assert "_siren_ward_config_ref()" in text
    assert 'git -C "$repo" rev-parse HEAD' in text
    assert "export WARD_CONFIG_REF=\"$(_siren_ward_config_ref)\"" in text


def test_cache_ref_strips_the_release_tag() -> None:
    image = f"{REGISTRY_BASE}-core:v0.243.0"
    assert cache_ref(image) == f"{REGISTRY_BASE}-core:buildcache"


def test_tier_files_chain_from_the_previous_tier_image() -> None:
    for tier in ("lang-node", "lang-go", "lang-dotnet", "ops", "agent", "full"):
        text = _tier_path(tier).read_text()
        assert f"FROM ${{BASE_IMAGE}} AS dev-base-{tier}" in text
        assert "ARG BASE_IMAGE" in text


def test_split_tiers_keep_their_managed_arg_defaults() -> None:
    expected_defaults = {
        "lang-node": ["ARG NODE_VERSION=22.23.1"],
        "lang-go": ["ARG GO_VERSION=1.26.5"],
        "lang-dotnet": ["ARG DOTNET_VERSION=10.0.301"],
        "ops": [
            "ARG AWSCLI_VERSION=2.35.15",
            "ARG GH_VERSION=2.96.0",
            "ARG DOCKER_VERSION=28.5.2",
            "ARG HELM_VERSION=4.2.2",
            "ARG KUBECTL_VERSION=1.36.2",
            "ARG YQ_VERSION=4.53.3",
            "ARG TAILSCALE_VERSION=1.98.8",
        ],
        "agent": [
            "ARG CLAUDE_VERSION=2.1.206",
            "ARG MCPORTER_VERSION=0.12.3",
            "ARG CODEX_VERSION=0.142.5",
            "ARG GOOSE_VERSION=1.41.0",
            "ARG OPENCODE_VERSION=1.17.18",
        ],
        "full": [
            "ARG GOLANGCI_LINT_VERSION=2.12.2",
            "ARG TRUFFLEHOG_VERSION=3.95.8",
            "ARG KDLFMT_VERSION=0.1.7",
        ],
    }

    for tier, arg_lines in expected_defaults.items():
        text = _tier_path(tier).read_text()
        for line in arg_lines:
            assert line in text


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


def test_pushed_build_uses_release_tagless_cache_ref(monkeypatch) -> None:
    script = _load_script()
    commands: list[list[str]] = []

    monkeypatch.setattr(script, "_run", lambda cmd: commands.append(cmd))
    monkeypatch.setattr(script, "_host_targetarch", lambda: "amd64")
    monkeypatch.setattr(script, "_ward_config_ref_commit", lambda: "abc123")

    script._build_plan(REGISTRY_BASE, "v0.243.0", True, "linux/amd64,linux/arm64")

    cache_refs = [
        arg
        for cmd in commands
        for arg in cmd
        if arg.startswith("type=registry,ref=")
    ]
    assert cache_refs
    assert all(":v0.243.0:buildcache" not in ref for ref in cache_refs)
    assert f"type=registry,ref={REGISTRY_BASE}-core:buildcache" in cache_refs
    assert f"type=registry,ref={REGISTRY_BASE}-full:buildcache,mode=max,ignore-error=true" in cache_refs
    assert any(
        "WARD_CONFIG_REF_COMMIT=abc123" in arg
        for cmd in commands
        for arg in cmd
    )

"""Tests for the dev-base image contract."""
from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

from agentic_os.dev_base import (
    DEV_BASE_ROOT,
    REGISTRY_BASE,
    PUBLISHED_TIER_NAMES,
    publish_plan,
    tier_tag,
)

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dev-base-build.py"

# Managed-ARG contract: NAMES are pinned here, VALUES derive from the Dockerfiles.
# Hard-pinned values deadlocked the daily dep-bump's own pytest gate (aos#452).
_ARG_DEFAULT_RE = re.compile(r"^ARG (?P<name>[A-Z0-9_]+)=(?P<value>\S+)\s*$", re.MULTILINE)
_VERSION_VALUE_RE = re.compile(r"^v?\d+[\w.\-]*$")


def _arg_defaults(tier: str) -> dict[str, str]:
    return {
        m.group("name"): m.group("value")
        for m in _ARG_DEFAULT_RE.finditer(_tier_path(tier).read_text())
    }


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
        f"{REGISTRY_BASE}:{tier}-{tag}" for tier in PUBLISHED_TIER_NAMES if tier != "full"
    ] + [f"{REGISTRY_BASE}:{tag}"]
    assert [entry["stage"] for entry in plan] == [
        f"dev-base-{tier}" for tier in PUBLISHED_TIER_NAMES
    ]
    assert [entry["dockerfile"] for entry in plan] == [
        f"docker/dev-base/{tier}/Dockerfile" for tier in PUBLISHED_TIER_NAMES
    ]
    assert [entry["base_image"] for entry in plan] == [
        "ubuntu:24.04",
        f"{REGISTRY_BASE}:core-{tag}",
        f"{REGISTRY_BASE}:lang-node-{tag}",
        f"{REGISTRY_BASE}:lang-go-{tag}",
        f"{REGISTRY_BASE}:lang-dotnet-{tag}",
        f"{REGISTRY_BASE}:ops-{tag}",
        f"{REGISTRY_BASE}:agent-{tag}",
    ]
    assert plan[-1]["tier"] == "full"
    assert "alias_image" not in plan[0]


def test_dev_base_plan_carries_per_tier_cache_and_alias_refs() -> None:
    plan = publish_plan(REGISTRY_BASE, "v0.242.0", "release")

    assert [entry["cache_image"] for entry in plan] == [
        f"{REGISTRY_BASE}:{tier_tag(tier, 'buildcache')}" for tier in PUBLISHED_TIER_NAMES
    ]
    assert [entry["alias_image"] for entry in plan] == [
        f"{REGISTRY_BASE}:{tier_tag(tier, 'release')}" for tier in PUBLISHED_TIER_NAMES
    ]
    assert plan[-1]["cache_image"] == f"{REGISTRY_BASE}:buildcache"
    assert plan[-1]["alias_image"] == f"{REGISTRY_BASE}:release"


def test_core_tier_keeps_the_hidden_ward_builder_stage() -> None:
    text = _tier_path("core").read_text()
    assert "AS dev-base-ward-builder" in text
    assert 'COPY --from=dev-base-ward-builder /usr/local/bin/ward /usr/local/bin/ward' in text
    ward_pin = _arg_defaults("core").get("WARD_VERSION")
    assert ward_pin and _VERSION_VALUE_RE.match(ward_pin)
    assert "ARG WARD_CONFIG_REF_COMMIT" in text
    assert "WARD_CONFIG_REF=forgejo.coilysiren.me/coilyco-flight-deck/agentic-os@${WARD_CONFIG_REF_COMMIT}//.ward" in text


def test_core_tier_runs_ward_doctor_after_installing_ward() -> None:
    text = _tier_path("core").read_text()
    assert (
        text.index('COPY --from=dev-base-ward-builder /usr/local/bin/ward /usr/local/bin/ward')
        < text.index("ward doctor")
    )
    assert "ward --version; \\\n    CLIGUARD_NO_SANDBOX=1 ward doctor; \\" in text


def test_shell_common_exports_a_live_file_ward_config_ref() -> None:
    text = (Path(__file__).resolve().parent.parent / "shell" / "common.sh").read_text()
    assert "_siren_ward_config_ref()" in text
    assert "printf 'file://%s/.ward'" in text
    assert "export WARD_CONFIG_REF=\"$(_siren_ward_config_ref)\"" in text


def test_tier_tag_keeps_full_plain_and_prefixes_variants() -> None:
    assert tier_tag("full", "v0.243.0") == "v0.243.0"
    assert tier_tag("full", "release") == "release"
    assert tier_tag("core", "v0.243.0") == "core-v0.243.0"
    assert tier_tag("lang-node", "release") == "lang-node-release"


def test_tier_files_chain_from_the_previous_tier_image() -> None:
    for tier in ("lang-node", "lang-go", "lang-dotnet", "ops", "agent", "full"):
        text = _tier_path(tier).read_text()
        assert f"FROM ${{BASE_IMAGE}} AS dev-base-{tier}" in text
        assert "ARG BASE_IMAGE" in text


def test_split_tiers_keep_their_managed_arg_defaults() -> None:
    expected_args = {
        "lang-node": ["NODE_VERSION"],
        "lang-go": ["GO_VERSION"],
        "lang-dotnet": ["DOTNET_VERSION"],
        "ops": [
            "AWSCLI_VERSION",
            "GH_VERSION",
            "DOCKER_VERSION",
            "HELM_VERSION",
            "KUBECTL_VERSION",
            "YQ_VERSION",
            "TAILSCALE_VERSION",
        ],
        "agent": [
            "CLAUDE_VERSION",
            "MCPORTER_VERSION",
            "CODEX_VERSION",
            "GOOSE_VERSION",
            "OPENCODE_VERSION",
        ],
        "full": [
            "GOLANGCI_LINT_VERSION",
            "TRUFFLEHOG_VERSION",
            "KDLFMT_VERSION",
        ],
    }

    for tier, names in expected_args.items():
        defaults = _arg_defaults(tier)
        for name in names:
            assert name in defaults, f"{tier}: managed ARG {name} vanished"
            assert _VERSION_VALUE_RE.match(defaults[name]), (
                f"{tier}: ARG {name}={defaults[name]} does not look like a pinned version"
            )


def test_agent_tier_still_copies_the_stable_assets_from_the_root_context() -> None:
    text = _tier_path("agent").read_text()
    assert "COPY agent-name.sh /opt/agentic-os/agent-name.sh" in text
    assert "COPY statusline.sh /opt/agentic-os/statusline.sh" in text
    assert "COPY statusline.d/ /opt/agentic-os/statusline.d/" in text
    assert "COPY ward-shell-entrypoint.sh /opt/agentic-os/ward-shell-entrypoint.sh" in text
    assert "COPY claude-managed-settings.json /etc/claude-code/managed-settings.json" in text
    assert "COPY substrate-image-repos.txt /tmp/substrate-image-repos.txt" in text
    assert 'ENTRYPOINT ["/opt/agentic-os/ward-shell-entrypoint.sh"]' in text


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
    assert all("v0.243.0" not in ref for ref in cache_refs)
    assert f"type=registry,ref={REGISTRY_BASE}:core-buildcache" in cache_refs
    assert f"type=registry,ref={REGISTRY_BASE}:buildcache,mode=max,ignore-error=true" in cache_refs
    assert any(
        "WARD_CONFIG_REF_COMMIT=abc123" in arg
        for cmd in commands
        for arg in cmd
    )


def test_pushed_build_tags_every_tier_with_the_branch_alias(monkeypatch) -> None:
    script = _load_script()
    commands: list[list[str]] = []

    monkeypatch.setattr(script, "_run", lambda cmd: commands.append(cmd))
    monkeypatch.setattr(script, "_host_targetarch", lambda: "amd64")
    monkeypatch.setattr(script, "_ward_config_ref_commit", lambda: "abc123")

    script._build_plan(REGISTRY_BASE, "v0.243.0", True, "linux/amd64,linux/arm64", "release")

    build_cmds = [cmd for cmd in commands if "--push" in cmd]
    assert len(build_cmds) == len(PUBLISHED_TIER_NAMES)
    for tier, cmd in zip(PUBLISHED_TIER_NAMES, build_cmds):
        tags = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-t"]
        assert tags == [
            f"{REGISTRY_BASE}:{tier_tag(tier, 'v0.243.0')}",
            f"{REGISTRY_BASE}:{tier_tag(tier, 'release')}",
        ]


def test_local_build_does_not_tag_an_alias(monkeypatch) -> None:
    script = _load_script()
    commands: list[list[str]] = []

    monkeypatch.setattr(script, "_run", lambda cmd: commands.append(cmd))
    monkeypatch.setattr(script, "_host_targetarch", lambda: "amd64")
    monkeypatch.setattr(script, "_ward_config_ref_commit", lambda: "abc123")

    script._build_plan("agentic-os", "dev-base-local", False, None)

    for cmd in commands:
        tags = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-t"]
        assert tags == [tag for tag in tags if tag.endswith("dev-base-local")]


def test_pushed_build_retries_a_flaky_tier_push(monkeypatch) -> None:
    script = _load_script()
    calls: list[list[str]] = []
    sleeps: list[int] = []
    state = {"failed_once": False}

    def flaky_run(cmd: list[str]) -> None:
        calls.append(cmd)
        if "--push" in cmd and not state["failed_once"]:
            state["failed_once"] = True
            raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(script, "_run", flaky_run)
    monkeypatch.setattr(script, "_sleep", sleeps.append)
    monkeypatch.setattr(script, "_ward_config_ref_commit", lambda: "abc123")

    script._build_plan(REGISTRY_BASE, "v0.243.0", True, "linux/amd64,linux/arm64")

    push_cmds = [cmd for cmd in calls if "--push" in cmd]
    assert len(push_cmds) == len(PUBLISHED_TIER_NAMES) + 1
    assert push_cmds[0] == push_cmds[1]
    assert sleeps == [15]


def test_pushed_build_gives_up_after_bounded_attempts(monkeypatch) -> None:
    script = _load_script()
    calls: list[list[str]] = []
    sleeps: list[int] = []

    def failing_run(cmd: list[str]) -> None:
        calls.append(cmd)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(script, "_run", failing_run)
    monkeypatch.setattr(script, "_sleep", sleeps.append)
    monkeypatch.setattr(script, "_ward_config_ref_commit", lambda: "abc123")

    with pytest.raises(subprocess.CalledProcessError):
        script._build_plan(REGISTRY_BASE, "v0.243.0", True, "linux/amd64,linux/arm64")

    assert len(calls) == script.PUSH_ATTEMPTS
    assert all(cmd == calls[0] for cmd in calls)
    assert sleeps == [15, 60]


def test_local_build_failure_does_not_retry(monkeypatch) -> None:
    script = _load_script()
    calls: list[list[str]] = []

    def failing_run(cmd: list[str]) -> None:
        calls.append(cmd)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(script, "_run", failing_run)
    monkeypatch.setattr(script, "_sleep", lambda seconds: pytest.fail("local build slept"))
    monkeypatch.setattr(script, "_host_targetarch", lambda: "amd64")
    monkeypatch.setattr(script, "_ward_config_ref_commit", lambda: "abc123")

    with pytest.raises(subprocess.CalledProcessError):
        script._build_plan("agentic-os", "dev-base-local", False, None)

    assert len(calls) == 1

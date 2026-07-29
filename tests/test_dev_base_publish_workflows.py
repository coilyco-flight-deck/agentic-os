"""Tests for the independent dev-base publish workflow surface."""

from __future__ import annotations

from pathlib import Path

from agentic_os.dev_base import PUBLISHED_TIER_NAMES


ROOT = Path(__file__).resolve().parent.parent
PUBLISH = ROOT / ".forgejo" / "workflows" / "dev-base-publish.yml"
RELEASE = ROOT / ".forgejo" / "workflows" / "release.yml"
PUBLISH_ACTION = ROOT / "actions" / "publish-dev-base" / "action.yml"
INSTALL_DOCKER = (
    ROOT
    / "actions"
    / "publish-dev-base"
    / "scripts"
    / "install-docker.sh"
)
VERIFY_FULL = (
    ROOT
    / "actions"
    / "publish-dev-base"
    / "scripts"
    / "verify-full.sh"
)


def _assert_alert_steps_are_non_blocking(text: str) -> None:
    lines = text.splitlines()
    alert_indexes = [
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("- name: Alert Telegram on")
    ]
    assert alert_indexes
    for index in alert_indexes:
        assert any(
            "continue-on-error: true" in line for line in lines[index : index + 8]
        )


def test_workflows_publish_parallel_languages_then_full() -> None:
    publish = PUBLISH.read_text(encoding="utf-8")
    release = RELEASE.read_text(encoding="utf-8")

    assert "publish-languages:" in publish
    assert "publish-full:" in publish
    assert "retag-languages:" in release
    assert "retag-full:" in release
    for tier in PUBLISHED_TIER_NAMES:
        if tier.startswith("lang-"):
            assert f"          - {tier}" in publish
            assert f"          - {tier}" in release
    assert "max-parallel: 4" in publish
    assert "tier: ${{ matrix.tier }}" in publish
    assert "tier: ${{ matrix.tier }}" in release
    assert "needs: [plan-draft, publish-languages]" in publish
    assert "needs: [plan-release, retag-languages, retag-full]" in release
    assert publish.count("uses: ./actions/publish-dev-base") == 2
    assert release.count("uses: ./actions/publish-dev-base") == 2


def test_publish_workflow_keeps_resume_inputs_and_non_blocking_alerts() -> None:
    publish = PUBLISH.read_text(encoding="utf-8")
    release = RELEASE.read_text(encoding="utf-8")

    for needle in ("sha:", "tag:", "continue-on-error: true"):
        assert needle in publish
    for needle in ("sha:", "tag:", "source-tag:", "continue-on-error: true"):
        assert needle in release
    assert "github.event.inputs.tier == 'all'" in publish
    assert "github.event.inputs.tier == 'full'" in publish
    _assert_alert_steps_are_non_blocking(publish)
    _assert_alert_steps_are_non_blocking(release)


def test_full_image_build_uses_the_dedicated_runner() -> None:
    publish = PUBLISH.read_text(encoding="utf-8")

    assert publish.count("runs-on: docker-build") == 2
    assert "publish-languages:" in publish
    assert "publish-full:" in publish
    assert "needs: [plan-draft, publish-languages]" in publish
    assert "plan-draft:\n    runs-on: docker\n" in publish


def test_shared_docker_bootstrap_retries_downloads_without_partial_files() -> None:
    script = INSTALL_DOCKER.read_text(encoding="utf-8")

    assert script.count("curl \\") == 1
    for option in (
        "--retry ",
        "--retry-all-errors",
        "--retry-delay ",
        "--remove-on-error",
        "-fsSL",
    ):
        assert option in script
    for source in (
        "download.docker.com/linux/static/stable/x86_64/",
        "download.docker.com/linux/static/stable/x86_64/docker-${docker_cli_ver}.tgz",
        "github.com/docker/buildx/releases/download/${BUILDX_VERSION}/",
    ):
        assert source in script
    assert "actions/install-docker-buildx" not in PUBLISH_ACTION.read_text(
        encoding="utf-8"
    )


def test_publish_action_verifies_every_toolchain_and_aosguard() -> None:
    action = PUBLISH_ACTION.read_text(encoding="utf-8")
    script = VERIFY_FULL.read_text(encoding="utf-8")

    assert "inputs:\n  tier:" in action
    assert "required: true" in action
    assert "Verify the full development surface on both architectures" in action
    assert "if: ${{ inputs.tier == 'full' }}" in action
    assert "scripts/verify-full.sh" in action
    assert 'image="${IMAGE_BASE}:${TAG}"' in script
    assert "linux/amd64 linux/arm64" in script
    for command in (
        "node --version",
        "go version",
        "dotnet --list-sdks",
        "cargo --version",
        "python --version",
        "aosguard --version",
        "test -s /opt/agentic-os/aosguard-skill/aosguard/SKILL.md",
        "test -s /opt/agentic-os/aosguard-skill/aosguard/references/commands.yaml",
    ):
        assert command in script

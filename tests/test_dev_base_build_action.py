"""Guard pull-request dev-base validation against publication drift."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATE_ACTION = ROOT / "actions" / "dev-base-build" / "action.yml"
PUBLISH_ACTION = ROOT / "actions" / "publish-dev-base" / "action.yml"
PUBLISH_IMAGE = (
    ROOT / "actions" / "publish-dev-base" / "scripts" / "publish-image.sh"
)
SETUP_BUILDER = (
    ROOT / "actions" / "publish-dev-base" / "scripts" / "setup-builder.sh"
)
VERIFY_FULL = (
    ROOT / "actions" / "publish-dev-base" / "scripts" / "verify-full.sh"
)
PLAN = ROOT / "actions" / "dev-base-build" / "scripts" / "plan.sh"
BUILD = ROOT / "actions" / "dev-base-build" / "scripts" / "build.sh"
CLEANUP = ROOT / "actions" / "dev-base-build" / "scripts" / "cleanup.sh"


def test_validation_action_has_no_registry_write_surface() -> None:
    text = VALIDATE_ACTION.read_text(encoding="utf-8")

    assert "registry-token" not in text
    assert "registry_token" not in text
    assert "REGISTRY_TOKEN" not in text
    assert "docker login" not in text
    assert "--push" not in text
    assert "secrets." not in text


def test_validation_and_publication_share_build_definitions() -> None:
    validate = VALIDATE_ACTION.read_text(encoding="utf-8")
    publish = PUBLISH_ACTION.read_text(encoding="utf-8")
    publish_image = PUBLISH_IMAGE.read_text(encoding="utf-8")

    for script in (
        "scripts/install-uv.sh",
        "scripts/install-docker.sh",
        "scripts/resolve-docker-host.sh",
        "scripts/setup-builder.sh",
        "scripts/verify-full.sh",
    ):
        assert script in validate
        assert script in publish
    assert "scripts/dev-base-build.py" in PLAN.read_text(encoding="utf-8")
    assert "scripts/dev-base-build.py" in BUILD.read_text(encoding="utf-8")
    assert "scripts/dev-base-build.py" in publish_image


def test_validation_bakes_one_local_platform_and_uses_the_affected_plan() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    build = BUILD.read_text(encoding="utf-8")

    assert "affected" in plan
    assert "--base \"$BASE_SHA\"" in plan
    assert "--local-bake" in build
    assert "--load" not in build
    assert '--platforms "$PLATFORM"' in build
    assert '--tiers "${tiers[@]}"' in build
    assert "INSTALL_BINFMT: \"false\"" in VALIDATE_ACTION.read_text(
        encoding="utf-8"
    )
    assert "BUILDER_NAME: aos-pr-builder" in VALIDATE_ACTION.read_text(
        encoding="utf-8"
    )


def test_validation_bounds_the_persistent_builder_cache() -> None:
    action = VALIDATE_ACTION.read_text(encoding="utf-8")
    cleanup = CLEANUP.read_text(encoding="utf-8")

    assert "cache-max:" in action
    assert "docker buildx prune" in cleanup
    assert '--builder "${BUILDER_NAME:-aos-pr-builder}"' in cleanup
    assert '--max-used-space "$CACHE_MAX"' in cleanup


def test_shared_builder_keeps_publication_multi_arch_capability() -> None:
    text = SETUP_BUILDER.read_text(encoding="utf-8")

    assert 'builder_name="${BUILDER_NAME:-aosbuilder}"' in text
    assert '${INSTALL_BINFMT:-true}' in text
    assert "tonistiigi/binfmt --install all" in text


def test_shared_full_verification_accepts_one_or_many_platforms() -> None:
    text = VERIFY_FULL.read_text(encoding="utf-8")

    assert "PLATFORMS:-linux/amd64,linux/arm64" in text
    assert 'for platform in "${platforms[@]}"' in text
    assert 'docker run --rm --platform "$platform"' in text

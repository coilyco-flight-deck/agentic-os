"""Shared dev-base tier metadata and release/build planning helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_BASE_ROOT = REPO_ROOT / "docker" / "dev-base"
REGISTRY_BASE = "forgejo.coilysiren.me/coilyco-flight-deck/agentic-os"
LOCAL_REGISTRY_BASE = "agentic-os"


@dataclass(frozen=True)
class TierSpec:
    tier: str
    stage: str
    dockerfile: Path
    base_tier: str | None
    published: bool = True

    @property
    def suffix(self) -> str:
        return self.tier

    @property
    def image_name(self) -> str:
        return f"agentic-os-{self.suffix}"


TIER_SPECS: tuple[TierSpec, ...] = (
    TierSpec(
        tier="core",
        stage="dev-base-core",
        dockerfile=DEV_BASE_ROOT / "core" / "Dockerfile",
        base_tier=None,
    ),
    TierSpec(
        tier="lang-node",
        stage="dev-base-lang-node",
        dockerfile=DEV_BASE_ROOT / "lang-node" / "Dockerfile",
        base_tier="core",
    ),
    TierSpec(
        tier="lang-go",
        stage="dev-base-lang-go",
        dockerfile=DEV_BASE_ROOT / "lang-go" / "Dockerfile",
        base_tier="lang-node",
    ),
    TierSpec(
        tier="lang-dotnet",
        stage="dev-base-lang-dotnet",
        dockerfile=DEV_BASE_ROOT / "lang-dotnet" / "Dockerfile",
        base_tier="lang-go",
    ),
    TierSpec(
        tier="ops",
        stage="dev-base-ops",
        dockerfile=DEV_BASE_ROOT / "ops" / "Dockerfile",
        base_tier="lang-dotnet",
    ),
    TierSpec(
        tier="agent",
        stage="dev-base-agent",
        dockerfile=DEV_BASE_ROOT / "agent" / "Dockerfile",
        base_tier="ops",
    ),
    TierSpec(
        tier="full",
        stage="dev-base-full",
        dockerfile=DEV_BASE_ROOT / "full" / "Dockerfile",
        base_tier="agent",
    ),
)

TIER_BY_NAME = {tier.tier: tier for tier in TIER_SPECS}
PUBLISHED_TIER_NAMES = tuple(tier.tier for tier in TIER_SPECS if tier.published)


def image_ref(registry_base: str, tier: str, tag: str) -> str:
    return f"{registry_base}-{tier}:{tag}"


def cache_ref(image: str) -> str:
    repository, sep, _tag = image.rpartition(":")
    if not sep:
        raise ValueError(f"expected tagged image ref, got {image!r}")
    return f"{repository}:buildcache"


def tier_dockerfile(tier: str) -> Path:
    return TIER_BY_NAME[tier].dockerfile


def publish_plan(registry_base: str, tag: str) -> list[dict[str, str | bool]]:
    plan: list[dict[str, str | bool]] = []
    images: dict[str, str] = {}
    for spec in TIER_SPECS:
        ref = image_ref(registry_base, spec.tier, tag)
        base_ref = "ubuntu:24.04" if spec.base_tier is None else images[spec.base_tier]
        plan.append(
            {
                "tier": spec.tier,
                "stage": spec.stage,
                "dockerfile": str(spec.dockerfile.relative_to(REPO_ROOT)),
                "image": ref,
                "base_image": base_ref,
                "published": spec.published,
            }
        )
        images[spec.tier] = ref
    return plan

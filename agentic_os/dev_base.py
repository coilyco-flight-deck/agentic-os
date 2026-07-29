"""Shared dev-base language-image metadata and release planning."""

from __future__ import annotations

from collections.abc import Iterable
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
    graft_tiers: tuple[str, ...] = ()
    shared_context: bool = False


TIER_SPECS: tuple[TierSpec, ...] = (
    TierSpec(
        "lang-node",
        "dev-base-lang-node",
        DEV_BASE_ROOT / "Dockerfile",
        None,
        shared_context=True,
    ),
    TierSpec(
        "lang-go",
        "dev-base-lang-go",
        DEV_BASE_ROOT / "Dockerfile",
        None,
        shared_context=True,
    ),
    TierSpec(
        "lang-dotnet",
        "dev-base-lang-dotnet",
        DEV_BASE_ROOT / "Dockerfile",
        None,
        shared_context=True,
    ),
    TierSpec(
        "lang-rust",
        "dev-base-lang-rust",
        DEV_BASE_ROOT / "Dockerfile",
        None,
        shared_context=True,
    ),
    TierSpec(
        "lang-python",
        "dev-base-lang-python",
        DEV_BASE_ROOT / "Dockerfile",
        None,
        shared_context=True,
    ),
    TierSpec(
        tier="full",
        stage="dev-base-full",
        dockerfile=DEV_BASE_ROOT / "full" / "Dockerfile",
        base_tier="lang-rust",
        graft_tiers=("lang-go", "lang-dotnet", "lang-python"),
    ),
)
TIER_BY_NAME = {spec.tier: spec for spec in TIER_SPECS}
PUBLISHED_TIER_NAMES = tuple(spec.tier for spec in TIER_SPECS)


def tier_tag(tier: str, tag: str) -> str:
    return tag if tier == "full" else f"{tier}-{tag}"


def image_ref(registry_base: str, tier: str, tag: str) -> str:
    return f"{registry_base}:{tier_tag(tier, tag)}"


def tier_dockerfile(tier: str) -> Path:
    return TIER_BY_NAME[tier].dockerfile


def graft_build_arg(tier: str) -> str:
    return f"{tier.replace('-', '_').upper()}_IMAGE"


def normalize_aliases(aliases: str | Iterable[str] | None = None) -> tuple[str, ...]:
    if aliases is None:
        return ()

    raw_aliases = (aliases,) if isinstance(aliases, str) else tuple(aliases)
    normalized: list[str] = []
    seen: set[str] = set()
    for alias in raw_aliases:
        clean_alias = str(alias).strip()
        if not clean_alias or clean_alias in seen:
            continue
        normalized.append(clean_alias)
        seen.add(clean_alias)
    return tuple(normalized)


def publish_plan(
    registry_base: str, tag: str, aliases: str | Iterable[str] | None = None
) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    alias_tags = normalize_aliases(aliases)
    images: dict[str, str] = {}
    for spec in TIER_SPECS:
        ref = image_ref(registry_base, spec.tier, tag)
        entry: dict[str, object] = {
            "tier": spec.tier,
            "stage": spec.stage,
            "dockerfile": spec.dockerfile.relative_to(REPO_ROOT).as_posix(),
            "context_dir": (
                DEV_BASE_ROOT if spec.shared_context else spec.dockerfile.parent
            ).relative_to(REPO_ROOT).as_posix(),
            "image": ref,
            "cache_image": image_ref(registry_base, spec.tier, "buildcache"),
            "base_image": (
                "ubuntu:24.04" if spec.base_tier is None else images[spec.base_tier]
            ),
            "graft_images": {
                graft_build_arg(tier): images[tier] for tier in spec.graft_tiers
            },
        }
        if alias_tags:
            alias_images = [
                image_ref(registry_base, spec.tier, alias) for alias in alias_tags
            ]
            entry["alias_images"] = alias_images
            entry["alias_image"] = alias_images[0]
        plan.append(entry)
        images[spec.tier] = ref
    return plan

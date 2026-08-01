#!/usr/bin/env python3
"""Build, publish, or promote the dev-base language-image family."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import re
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Callable

from agentic_os.dev_base import (
    PUBLISHED_TIER_NAMES,
    REGISTRY_BASE,
    affected_tiers,
    publish_plan,
    required_build_tiers,
)


_DIGEST_RE = re.compile(r"^Digest:\s+(sha256:[0-9a-f]+)$", re.MULTILINE)
_MANIFEST_NOT_FOUND_RE = re.compile(r"\b404 Not Found\b", re.IGNORECASE)
_MANIFEST_INSPECT_TIMEOUT_SECONDS = 30


def _docker_base_command(
    push: bool, platforms: str | None, *, load: bool = False
) -> list[str]:
    if push:
        cmd = ["docker", "buildx", "build", "--progress=plain", "--push"]
        if platforms:
            cmd.extend(["--platform", platforms])
        return cmd
    if load:
        requested_platforms = [
            value.strip() for value in (platforms or "").split(",") if value.strip()
        ]
        if len(requested_platforms) != 1:
            raise SystemExit("buildx load requires exactly one platform")
        return [
            "docker",
            "buildx",
            "build",
            "--progress=plain",
            "--load",
            "--platform",
            requested_platforms[0],
        ]
    return ["docker", "build"]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _retry(
    action: str,
    func: Callable[[], object],
    attempts: int = 4,
    initial_delay: int = 2,
) -> object:
    delay = initial_delay
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            result = func()
        except subprocess.CalledProcessError as exc:
            last_exc = exc
            if attempt == attempts:
                break
            print(
                (
                    f"::notice::retrying {action} after attempt "
                    f"{attempt}/{attempts} failed; sleeping {delay}s"
                ),
                file=sys.stderr,
            )
            time.sleep(delay)
            delay = min(delay * 2, 30)
            continue
        if attempt > 1:
            print(
                f"::notice::{action} succeeded after attempt {attempt}/{attempts}",
                file=sys.stderr,
            )
            _append_step_summary(
                f"- {action} succeeded after attempt {attempt}/{attempts}\n"
            )
        return result
    assert last_exc is not None
    raise last_exc


def _inspect_manifest_once(
    ref: str, *, allow_missing: bool = False
) -> subprocess.CompletedProcess[str] | None:
    cmd = ["docker", "buildx", "imagetools", "inspect", ref]
    try:
        probe = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=_MANIFEST_INSPECT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise subprocess.CalledProcessError(
            124,
            cmd,
            output=exc.stdout,
            stderr=exc.stderr,
        ) from exc
    except OSError as exc:
        raise subprocess.CalledProcessError(127, cmd, stderr=str(exc)) from exc
    if probe.returncode != 0:
        output = getattr(probe, "stdout", "")
        error = getattr(probe, "stderr", "")
        if allow_missing and _MANIFEST_NOT_FOUND_RE.search(f"{output}\n{error}"):
            return None
        raise subprocess.CalledProcessError(
            probe.returncode,
            cmd,
            output=output,
            stderr=error,
        )
    return probe


def _inspect_manifest(
    ref: str, attempts: int = 3, initial_delay: int = 1
) -> str | None:
    try:
        probe = _retry(
            f"inspect manifest {ref}",
            lambda: _inspect_manifest_once(ref, allow_missing=True),
            attempts=attempts,
            initial_delay=initial_delay,
        )
    except subprocess.CalledProcessError:
        return None
    if probe is None:
        return None
    stdout = getattr(probe, "stdout", "")
    stderr = getattr(probe, "stderr", "")
    match = _DIGEST_RE.search(stdout) or _DIGEST_RE.search(stderr)
    if match is None:
        return None
    return match.group(1)


def _cache_refs(buildcache_ref: str) -> tuple[str, str]:
    cache_from = f"type=registry,ref={buildcache_ref}"
    cache_to = f"{cache_from},mode=max,ignore-error=true"
    return cache_from, cache_to


def _append_cache_summary(
    tier: str,
    buildcache_ref: str,
    provenance: str | None,
    *,
    write_state: str | None = None,
) -> None:
    cache_from, cache_to = _cache_refs(buildcache_ref)
    lines = [
        f"### {tier} cache plan",
        "",
        f"- cache key: {buildcache_ref}",
        f"- cache source: {cache_from}",
        f"- cache destination: {cache_to}",
        (
            f"- cache source provenance: {provenance}"
            if provenance is not None
            else "- cache source provenance: miss or unavailable"
        ),
    ]
    if write_state is not None:
        lines.extend(
            [
                "",
                f"### {tier} cache result",
                "",
                f"- cache key: {buildcache_ref}",
                f"- cache write: {write_state}",
            ]
        )
    _append_step_summary("\n".join(lines) + "\n")


def _probe_cache_write(buildcache_ref: str) -> bool:
    # cache-to runs with ignore-error=true so a registry hiccup cannot fail the
    # push. Probe the cache manifest and warn loudly so a cold cache is visible.
    if _inspect_manifest(buildcache_ref) is None:
        print(
            f"::warning::buildcache write to {buildcache_ref} failed or is "
            "missing - the next full-image build starts cold. "
            "imagetools inspect could not resolve the cache manifest.",
            file=sys.stderr,
        )
        return False
    return True


def _wait_for_source_image(
    source_ref: str, attempts: int = 5, initial_delay: int = 5
) -> None:
    def _inspect_once() -> None:
        _inspect_manifest_once(source_ref)

    _retry(
        f"wait for draft image {source_ref}",
        _inspect_once,
        attempts=attempts,
        initial_delay=initial_delay,
    )


def _has_target_checkpoint(target_ref: str, alias_refs: Sequence[str]) -> bool:
    target = _inspect_manifest(target_ref)
    if target is None:
        return False
    if not alias_refs:
        return True
    aliases = [_inspect_manifest(alias_ref) for alias_ref in alias_refs]
    return all(alias is not None and alias == target for alias in aliases)


def _target_matches_source(
    target_ref: str, source_ref: str, alias_refs: Sequence[str]
) -> bool:
    target = _inspect_manifest(target_ref)
    source = _inspect_manifest(source_ref)
    if target is None or source is None:
        return False
    if target != source:
        return False
    aliases = [_inspect_manifest(alias_ref) for alias_ref in alias_refs]
    return all(alias is not None and alias == source for alias in aliases)


def _append_step_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write(text)


def _host_targetarch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise SystemExit(f"unsupported host architecture: {machine}")


def _build_plan(
    registry_base: str,
    tag: str,
    push: bool,
    platforms: str | None,
    aliases: str | Sequence[str] | None = None,
    only_tier: str | None = None,
    *,
    load: bool = False,
    only_tiers: Sequence[str] | None = None,
) -> None:
    if push and load:
        raise SystemExit("--push and --load cannot be combined")
    plan = publish_plan(registry_base, tag, aliases)
    if only_tier is not None and only_tiers:
        raise SystemExit("--tier and --tiers cannot be combined")
    selected_tiers = (
        {only_tier}
        if only_tier is not None
        else set(only_tiers or ())
    )
    unknown_tiers = selected_tiers.difference(PUBLISHED_TIER_NAMES)
    if unknown_tiers:
        raise SystemExit(f"unknown tier: {', '.join(sorted(unknown_tiers))}")
    if selected_tiers:
        plan = [entry for entry in plan if entry["tier"] in selected_tiers]
    for entry in plan:
        dockerfile = Path(entry["dockerfile"])
        context_dir = Path(entry["context_dir"])
        alias_images = tuple(entry.get("alias_images", ()))
        buildcache_ref = str(entry["cache_image"])
        cache_from, cache_to = _cache_refs(buildcache_ref)
        if push and _has_target_checkpoint(entry["image"], alias_images):
            print(
                f"{entry['tier']} already published at {entry['image']}; "
                "skipping image"
            )
            continue
        cmd = _docker_base_command(push, platforms, load=load)
        is_language = str(entry["tier"]).startswith("lang-")
        if is_language and not push and not load:
            cmd.extend(["--build-arg", f"TARGETARCH={_host_targetarch()}"])
        if is_language:
            cmd.extend(
                [
                    "--build-context",
                    "aos-cli=aos",
                    "--build-context",
                    "aosguard-spec=.specgen",
                    "--build-context",
                    "aosguard-python=agentic_os",
                    "--build-context",
                    "repo-lists=aos/repositories",
                ]
            )
        else:
            cmd.extend(["--build-arg", f"BASE_IMAGE={entry['base_image']}"])
        for arg_name, graft_ref in entry["graft_images"].items():
            cmd.extend(["--build-arg", f"{arg_name}={graft_ref}"])
        if push:
            cmd.extend(["--cache-from", cache_from, "--cache-to", cache_to])
        cmd.extend(["-t", entry["image"]])
        if push:
            for alias_image in entry.get("alias_images", []):
                cmd.extend(["-t", alias_image])
        cmd.extend(["--target", str(entry["stage"])])
        cmd.extend(["-f", str(dockerfile), str(context_dir)])
        if push:
            summary = "\n".join(
                [
                    f"### {entry['tier']} publish context",
                    "",
                    f"- image: {entry['image']}",
                    f"- cache: {entry['cache_image']}",
                    f"- context: {entry['context_dir']}",
                    f"- command: {shlex.join(cmd)}",
                    "",
                ]
            )
            print("::group::dev-base publish context")
            print(f"image={entry['image']}")
            print(f"cache={entry['cache_image']}")
            print(f"context={entry['context_dir']}")
            print(f"command={shlex.join(cmd)}")
            print("::endgroup::")
            _append_step_summary(summary + "\n")
        if push:
            provenance = _inspect_manifest(buildcache_ref)
            print(f"::group::{entry['tier']} cache plan")
            print(f"tier={entry['tier']}")
            print(f"cache_key={buildcache_ref}")
            print(f"cache_source={cache_from}")
            print(f"cache_destination={cache_to}")
            print(
                "cache_source_provenance="
                + (provenance if provenance is not None else "miss or unavailable")
            )
            print("::endgroup::")
            _append_cache_summary(entry["tier"], buildcache_ref, provenance)
        if push:
            _retry(f"build {entry['tier']}", lambda: _run(cmd))
        else:
            _run(cmd)
        if push:
            _retry(
                f"inspect built image {entry['image']}",
                lambda: _inspect_manifest_once(entry["image"]),
            )
            for alias_image in alias_images:
                _retry(
                    f"inspect built alias {alias_image}",
                    lambda alias_image=alias_image: _inspect_manifest_once(
                        alias_image
                    ),
                )
            write_state = "verified" if _probe_cache_write(buildcache_ref) else "missing"
            _append_cache_summary(
                entry["tier"], buildcache_ref, provenance, write_state=write_state
            )


def _local_bake_definition(
    registry_base: str,
    tag: str,
    platform_name: str,
    tiers: Sequence[str],
) -> dict[str, object]:
    requested_platforms = [
        value.strip() for value in platform_name.split(",") if value.strip()
    ]
    if len(requested_platforms) != 1:
        raise SystemExit("local bake requires exactly one platform")

    selected_tiers = required_build_tiers(tiers)
    plan = {
        str(entry["tier"]): entry
        for entry in publish_plan(registry_base, tag)
        if entry["tier"] in selected_tiers
    }
    tier_by_image = {
        str(entry["image"]): tier for tier, entry in plan.items()
    }
    targets: dict[str, object] = {}
    for tier in selected_tiers:
        entry = plan[tier]
        contexts: dict[str, str] = {}
        if tier.startswith("lang-"):
            contexts = {
                "aos-cli": "aos",
                "aosguard-spec": ".specgen",
                "aosguard-python": "agentic_os",
                "repo-lists": "aos/repositories",
            }
        else:
            dependency_refs = [
                str(entry["base_image"]),
                *(str(ref) for ref in entry["graft_images"].values()),
            ]
            contexts = {
                ref: f"target:{tier_by_image[ref]}" for ref in dependency_refs
            }

        args = (
            {}
            if tier.startswith("lang-")
            else {
                "BASE_IMAGE": str(entry["base_image"]),
                **{
                    str(name): str(ref)
                    for name, ref in entry["graft_images"].items()
                },
            }
        )
        targets[tier] = {
            "context": str(entry["context_dir"]),
            "dockerfile": Path(str(entry["dockerfile"])).name,
            "target": str(entry["stage"]),
            "tags": [str(entry["image"])],
            "platforms": requested_platforms,
            "contexts": contexts,
            "args": args,
            "output": ["type=docker" if tier == "full" else "type=cacheonly"],
        }

    return {
        "group": {"default": {"targets": list(selected_tiers)}},
        "target": targets,
    }


def _build_local_bake(
    registry_base: str,
    tag: str,
    platform_name: str,
    tiers: Sequence[str],
) -> None:
    definition = _local_bake_definition(
        registry_base,
        tag,
        platform_name,
        tiers,
    )
    subprocess.run(
        ["docker", "buildx", "bake", "--progress=plain", "--file", "-"],
        check=True,
        input=json.dumps(definition),
        text=True,
    )


def _promote_plan(
    registry_base: str,
    source_tag: str,
    target_tag: str,
    aliases: str | Sequence[str] | None = None,
    only_tier: str | None = None,
) -> None:
    source_plan = publish_plan(registry_base, source_tag)
    target_plan = {
        entry["tier"]: entry
        for entry in publish_plan(registry_base, target_tag, aliases)
    }
    if only_tier is not None:
        source_plan = [entry for entry in source_plan if entry["tier"] == only_tier]
        if not source_plan:
            raise SystemExit(f"unknown tier: {only_tier}")
    for source_entry in source_plan:
        target_entry = target_plan[source_entry["tier"]]
        target_images = [target_entry["image"], *target_entry.get("alias_images", [])]
        if _target_matches_source(
            target_entry["image"],
            source_entry["image"],
            target_entry.get("alias_images", []),
        ):
            print(
                (
                    f"{source_entry['tier']} already promoted to "
                    f"{target_entry['image']}; skipping image"
                )
            )
            continue
        _wait_for_source_image(source_entry["image"])
        cmd = ["docker", "buildx", "imagetools", "create"]
        for target_image in target_images:
            cmd.extend(["-t", target_image])
        cmd.append(source_entry["image"])
        _retry(
            f"promote {source_entry['tier']} -> {target_entry['image']}",
            lambda: _run(cmd),
        )
        for target_image in target_images:
            _retry(
                f"inspect promoted image {target_image}",
                lambda target_image=target_image: _inspect_manifest_once(
                    target_image
                ),
            )


def _cmd_plan(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "registry_base": args.registry,
                "tag": args.tag,
                "tiers": publish_plan(args.registry, args.tag, args.alias),
            }
        )
    )
    return 0


def _changed_paths(base: str, head: str) -> tuple[str, ...]:
    probe = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACDMR",
            base,
            head,
            "--",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line for line in probe.stdout.splitlines() if line)


def _cmd_affected(args: argparse.Namespace) -> int:
    if args.changed_path and args.base:
        raise SystemExit("--changed-path and --base cannot be combined")

    if args.changed_path:
        paths = tuple(args.changed_path)
        selected = affected_tiers(paths)
    elif args.base:
        paths = _changed_paths(args.base, args.head)
        selected = affected_tiers(paths)
    else:
        paths = ()
        selected = PUBLISHED_TIER_NAMES

    build_tiers = required_build_tiers(selected)
    payload = {
        "changed_paths": list(paths),
        "affected_tiers": list(selected),
        "build_tiers": list(build_tiers),
    }
    print(json.dumps(payload))
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as output:
            output.write(f"affected_tiers={' '.join(selected)}\n")
            output.write(f"build_tiers={' '.join(build_tiers)}\n")
            output.write(f"has_work={'true' if build_tiers else 'false'}\n")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    if args.local_bake:
        if args.push or args.load or args.tier is not None:
            raise SystemExit(
                "--local-bake requires --tiers and cannot combine with "
                "--push, --load, or --tier"
            )
        if not args.tiers:
            raise SystemExit("--local-bake requires --tiers")
        _build_local_bake(
            args.registry,
            args.tag,
            args.platforms,
            args.tiers,
        )
        return 0
    _build_plan(
        args.registry,
        args.tag,
        args.push,
        args.platforms,
        args.alias,
        args.tier,
        load=args.load,
        only_tiers=args.tiers,
    )
    return 0


def _cmd_promote(args: argparse.Namespace) -> int:
    _promote_plan(args.registry, args.source_tag, args.tag, args.alias, args.tier)
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    plan = publish_plan(args.registry, args.tag, args.alias)
    if args.tier is not None:
        plan = [entry for entry in plan if entry["tier"] == args.tier]
        if not plan:
            raise SystemExit(f"unknown tier: {args.tier}")
    if len(plan) != 1:
        raise SystemExit("check requires exactly one image")

    target_entry = plan[0]
    alias_images = tuple(target_entry.get("alias_images", ()))
    if args.mode == "build":
        return 0 if _has_target_checkpoint(target_entry["image"], alias_images) else 1

    if not args.source_tag:
        raise SystemExit("source-tag is required in promote mode")
    source_plan = publish_plan(args.registry, args.source_tag)
    if args.tier is not None:
        source_plan = [entry for entry in source_plan if entry["tier"] == args.tier]
    if len(source_plan) != 1:
        raise SystemExit("promote check requires exactly one image")
    source_entry = source_plan[0]
    return (
        0
        if _target_matches_source(
            target_entry["image"], source_entry["image"], alias_images
        )
        else 1
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        default=REGISTRY_BASE,
        help="Registry/image base (default: Forgejo release registry).",
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Release tag or local tag to stamp onto the image.",
    )
    parser.add_argument(
        "--alias",
        action="append",
        default=[],
        help="Moving alias tag pushed alongside the stamped tag. May be repeated.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Print the derived image plan as JSON.")
    p_plan.set_defaults(func=_cmd_plan)

    p_affected = sub.add_parser(
        "affected",
        help="Derive the affected tiers and their local build closure.",
    )
    p_affected.add_argument(
        "--base",
        default="",
        help="Base revision for a git changed-path diff.",
    )
    p_affected.add_argument(
        "--head",
        default="HEAD",
        help="Head revision for a git changed-path diff.",
    )
    p_affected.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="Explicit changed path. May be repeated instead of --base.",
    )
    p_affected.add_argument(
        "--github-output",
        default="",
        help="Optional GitHub/Forgejo Actions output file.",
    )
    p_affected.set_defaults(func=_cmd_affected)

    p_build = sub.add_parser("build", help="Build the image family in order.")
    p_build.add_argument(
        "--push",
        action="store_true",
        help="Push the image instead of loading it locally.",
    )
    p_build.add_argument(
        "--tier",
        default=None,
        choices=PUBLISHED_TIER_NAMES,
        help="Build only this tier. Its source tiers must already exist.",
    )
    p_build.add_argument(
        "--tiers",
        nargs="+",
        default=[],
        choices=PUBLISHED_TIER_NAMES,
        help="Build an ordered tier closure derived by the affected command.",
    )
    p_build.add_argument(
        "--load",
        action="store_true",
        help="Use buildx to load one local architecture into the Docker daemon.",
    )
    p_build.add_argument(
        "--local-bake",
        action="store_true",
        help=(
            "Build a local target graph in BuildKit and load only the full image."
        ),
    )
    p_build.add_argument(
        "--platforms",
        default="linux/amd64,linux/arm64",
        help="Platforms for buildx push or load operations.",
    )
    p_build.set_defaults(func=_cmd_build)

    p_promote = sub.add_parser("promote", help="Retag an already-pushed image family.")
    p_promote.add_argument(
        "--source-tag",
        required=True,
        help="Existing tag to retag from, usually the draft tag built on main.",
    )
    p_promote.add_argument(
        "--tier",
        default=None,
        choices=PUBLISHED_TIER_NAMES,
        help="Promote only this tier.",
    )
    p_promote.set_defaults(func=_cmd_promote)

    p_check = sub.add_parser(
        "check",
        help=(
            "Report whether the requested tier matches its target checkpoint."
        ),
    )
    p_check.add_argument("--mode", required=True, choices=("build", "promote"))
    p_check.add_argument(
        "--tier",
        default=None,
        choices=PUBLISHED_TIER_NAMES,
        help="Check only this tier.",
    )
    p_check.add_argument(
        "--source-tag",
        default="",
        help="Existing source tag used by promote mode.",
    )
    p_check.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

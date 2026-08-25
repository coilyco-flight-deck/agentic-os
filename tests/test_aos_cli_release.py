"""Exercise the standalone aos release metadata contract."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent.parent
TARGETS = ROOT / "aos-cli" / "release-targets.txt"
RELEASE_BINARIES = (
    "aos",
    "aoscompose",
    "aosward",
    "aosguard",
    "aterm",
)


def release_targets() -> list[str]:
    return [
        line.strip()
        for line in TARGETS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def artifact_name(target: str, program: str = "aos") -> str:
    goos, goarch = target.split("/")
    suffix = ".exe" if goos == "windows" else ""
    return f"{program}-{goos}-{goarch}{suffix}"


def test_release_target_manifest_is_safe_and_unique() -> None:
    targets = release_targets()

    assert targets
    assert len(targets) == len(set(targets))
    assert all(
        re.fullmatch(r"[a-z0-9_-]+/[a-z0-9_-]+", target) for target in targets
    )


def test_packaging_covers_every_release_binary(tmp_path: Path) -> None:
    for target in release_targets():
        for program in RELEASE_BINARIES:
            name = artifact_name(target, program)
            (tmp_path / name).write_bytes(f"{program}:{target}".encode())

    version = "aos-v1.2.3"
    env = os.environ | {
        "AOS_RELEASE_DIST": str(tmp_path),
        "AOS_RELEASE_VERSION": version,
    }
    subprocess.run(
        ["sh", str(ROOT / "scripts" / "render-aos-packaging.sh")],
        check=True,
        cwd=ROOT,
        env=env,
    )

    formula = (tmp_path / "aos.rb").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "aos.json").read_text(encoding="utf-8"))
    rendered = formula + json.dumps(manifest)
    for target in release_targets():
        for program in RELEASE_BINARIES:
            digest = hashlib.sha256(
                (tmp_path / artifact_name(target, program)).read_bytes()
            ).hexdigest()
            assert digest in rendered

    assert manifest["version"] == version.removeprefix("aos-v")
    assert f"/releases/download/{version}/" in rendered
    bins = manifest["architecture"]["64bit"]["bin"]
    assert ["aoscompose-windows-amd64.exe", "aoscompose"] in bins
    assert ["aoscompose-windows-amd64.exe", "aoscomposed"] in bins
    assert ["aosward-windows-amd64.exe", "aosward"] in bins
    assert ["aosguard-windows-amd64.exe", "aosguard"] in bins
    assert ["aterm-windows-amd64.exe", "aterm"] in bins
    assert 'bin.install_symlink bin/"aoscompose" => "aoscomposed"' in formula
    for program in RELEASE_BINARIES[1:]:
        assert f'resource("{program}")' in formula


def test_release_check_family_list_matches_the_released_binaries() -> None:
    """The release train once went red on a bare artifact multiplier.

    check-aos-release.sh asserts a checksum count of targets x families. That
    total lived as a literal, so retiring a binary left it stale and the failure
    only surfaced after promote, in the release job. Pin the list here so ci.yml
    catches the drift on the pull request instead.
    """
    release_check = (ROOT / "scripts" / "check-aos-release.sh").read_text(
        encoding="utf-8"
    )
    match = re.search(r'^release_families="([^"]+)"', release_check, re.MULTILINE)
    assert match, "check-aos-release.sh must declare release_families"
    families = set(match.group(1).split())
    assert families == set(RELEASE_BINARIES) | {"aos-bundle"}

    # The builder globs the same families into SHA256SUMS. A family missing
    # there is caught by the count above only at release time.
    builder = (ROOT / "scripts" / "aos-release-build.sh").read_text(encoding="utf-8")
    glob_line = re.search(r"^\s*for asset in ((?:\S+\*\s*)+);", builder, re.MULTILINE)
    assert glob_line, "aos-release-build.sh must glob release assets for SHA256SUMS"
    prefixes = [g.rstrip("*") for g in glob_line.group(1).split()]
    for family in sorted(families):
        assert any(
            f"{family}-".startswith(prefix) for prefix in prefixes
        ), f"{family} has no checksum glob in aos-release-build.sh: {prefixes}"


def test_release_workflow_derives_assets_from_dist() -> None:
    workflow = (
        ROOT / ".forgejo" / "workflows" / "aos-cli-release.yml"
    ).read_text(encoding="utf-8")
    workflow_script = (ROOT / "scripts" / "ci" / "aos-cli-release.sh").read_text(
        encoding="utf-8"
    )
    builder = (ROOT / "scripts" / "aos-release-build.sh").read_text(
        encoding="utf-8"
    )

    assert "for asset in dist/*" in workflow_script
    assert "release-targets.txt" in builder
    assert "build_aosguard" in builder
    assert "build_aosguard_skill" in builder
    assert "build_bundle" in builder
    assert "aos-bundle-${goos}-${goarch}.tar.gz" in builder
    assert "build_aterm" in builder
    assert "compiledHarnessLaunchProfilesBase64" in builder
    assert "specverb.lock" in builder
    assert "aosguard-*" in builder
    assert "aterm-*" in builder
    assert 'host_suffix=".exe"' in builder
    assert "shasum -a 256 -c -" in builder
    assert "go env GOOS | tr -d" in builder
    assert 'target=$(printf' in builder
    assert "scripts/ci/aos-cli-release.sh" in workflow
    assert "just aos-release-build" in workflow_script
    assert "just aos-release-package" in workflow_script
    assert "just aterm-test" in workflow_script
    release_check = (ROOT / "scripts" / "check-aos-release.sh").read_text(encoding="utf-8")
    assert 'grep -Fx "aosguard version $version"' in release_check
    assert 'grep -Fx "aterm version $version"' in release_check
    assert "share/aos/aosguard-skill/aosguard/SKILL.md" in release_check
    assert "--dry-run" in release_check
    assert "agent-compose" in release_check
    assert "--aos-bin" in release_check
    assert "ops actions --help" in release_check
    assert "aterm.launch.v1" in release_check
    assert "aterm accepted a role that is not on the roster" in release_check
    assert '"_session"' in release_check


def test_specgen_pin_is_owned_by_the_dependency_lock() -> None:
    lock = json.loads(
        (ROOT / ".specgen" / "guardfiles" / "specverb.lock").read_text(
            encoding="utf-8"
        )
    )
    pinned = lock["cliGuard"].removeprefix("v")
    builder = (ROOT / "scripts" / "aos-release-build.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "docker" / "dev-base" / "full" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert not (ROOT / "aos-cli" / "release.env").exists()
    assert '"cliGuard"' in builder
    assert "SPECGEN_VERSION" not in builder
    assert f"ARG SPECGEN_VERSION={pinned}\n" in dockerfile

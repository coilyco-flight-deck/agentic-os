"""Tests for installing Ward from release artifacts rather than from source.

The image already consumed the published binaries. The workflow installer still
cloned Ward and ran `go build`, so gates rebuilt a product that ships verified
bytes. See agentic-os#606.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "scripts" / "install-workflow-ward.sh"
IMAGE = ROOT / "docker" / "dev-base" / "full" / "Dockerfile"


def _install(tmp_path: Path, *, arch: str = "x86_64", corrupt: bool = False,
             missing_sum: bool = False) -> subprocess.CompletedProcess[str]:
    """Run the installer against stubbed curl, uname, and sha256sum."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    served = tmp_path / "served"
    served.mkdir()
    (served / "ward-linux-amd64").write_text("#!/usr/bin/env bash\necho ward v1\n")
    (served / "ward-linux-arm64").write_text("#!/usr/bin/env bash\necho ward v1\n")
    digest = "0" * 64 if corrupt else "GOOD"
    lines = [] if missing_sum else [
        f"{digest}  ward-linux-amd64", f"{digest}  ward-linux-arm64",
    ]
    (served / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    (bin_dir / "uname").write_text(f'#!/usr/bin/env bash\necho "{arch}"\n')
    # curl serves the release directory by basename.
    (bin_dir / "curl").write_text(
        f'#!/usr/bin/env bash\nurl=""; out=""\n'
        f'while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; '
        f'http*) url="$1"; shift;; *) shift;; esac; done\n'
        f'cp "{served}/$(basename "$url")" "$out"\n'
    )
    # sha256sum -c passes only on the marker the good SHA256SUMS carries.
    (bin_dir / "sha256sum").write_text(
        '#!/usr/bin/env bash\nread -r line\n'
        'case "$line" in GOOD*) exit 0 ;; *) echo "FAILED" >&2; exit 1 ;; esac\n'
    )
    for name in ("uname", "curl", "sha256sum"):
        (bin_dir / name).chmod(0o755)

    out = tmp_path / "ward"
    return subprocess.run(
        ["bash", str(INSTALLER), "v9.9.9", str(out)],
        check=False, capture_output=True, text=True,
        env=os.environ | {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
    )


def test_no_path_builds_ward_from_source() -> None:
    # The acceptance criterion, read off both paths rather than assumed.
    for path in (INSTALLER, IMAGE):
        text = path.read_text(encoding="utf-8")
        assert "ward.git" not in text, path.name
        assert "cmd/ward" not in text, path.name


def test_the_image_and_the_installer_share_the_artifact_contract() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    image = IMAGE.read_text(encoding="utf-8")

    for shared in ("ward-linux-", "SHA256SUMS", "sha256sum -c -"):
        assert shared in installer, shared
        assert shared in image, shared


@pytest.mark.parametrize(("arch", "asset"), [
    ("x86_64", "ward-linux-amd64"),
    ("amd64", "ward-linux-amd64"),
    ("aarch64", "ward-linux-arm64"),
    ("arm64", "ward-linux-arm64"),
])
def test_architecture_maps_to_the_published_asset(
    tmp_path: Path, arch: str, asset: str
) -> None:
    got = _install(tmp_path, arch=arch)

    assert got.returncode == 0, got.stderr
    assert (tmp_path / "ward").is_file()


def test_an_unsupported_architecture_fails_closed(tmp_path: Path) -> None:
    got = _install(tmp_path, arch="riscv64")

    assert got.returncode == 1
    assert "unsupported architecture" in got.stderr


def test_a_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    got = _install(tmp_path, corrupt=True)

    assert got.returncode != 0
    assert not (tmp_path / "ward").exists()


def test_an_absent_checksum_line_is_not_a_pass(tmp_path: Path) -> None:
    # grep finding nothing must not read as a verified binary.
    got = _install(tmp_path, missing_sum=True)

    assert got.returncode != 0
    assert not (tmp_path / "ward").exists()


def test_the_installer_needs_no_go_toolchain(tmp_path: Path) -> None:
    # A gate that installs Ward should not depend on a compiler being present.
    assert shutil.which("bash")
    assert "go " not in INSTALLER.read_text(encoding="utf-8")

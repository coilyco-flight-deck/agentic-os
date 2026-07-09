"""Validate the coilyco ward-specs bundle shape.

This checks the authored bundle in `.ward/` plus the release tarball file list
so a future edit cannot silently flip every repo into a PR workflow or drop the
ward-only override from the published asset.
"""

from __future__ import annotations

import sys
from pathlib import Path

HOOK_ID = "ward-specs-bundle"

ROOT = Path(".")
DEFAULTS_PATH = ROOT / ".ward" / "ward-kdl.defaults.kdl"
RELEASE_PATH = ROOT / ".forgejo" / "workflows" / "release.yml"
EXPECTED_DEFAULTS = """smart-defaults {
    agent-reservation-ttl "1h"
    agent-reservation-recheck-max "15s"
    agent-reap-idle "1h"
    agent-reap-max-cpu "5.0"
    director-max-parallel "10"
    director-limit "50"
    director-poll-interval "30s"
    reviewer-timeout "8m"
    config-bundle-ttl "600"
    container-assets-ttl "1h"
    container-read-only-extra-repo-ttl "24h"
    container-reap-keep "10"
    agent-workflow default="direct-main" {
        repo "coilyco-flight-deck/ward" workflow="pull-requests-and-merge"
    }
}
"""
EXPECTED_TAR_MEMBER = "./ward-kdl.defaults.kdl"


def fail(msg: str) -> None:
    print(f"check-ward-specs-bundle: {msg}")
    sys.exit(1)


def _require(condition: bool, msg: str) -> None:
    if not condition:
        fail(msg)


def _validate_defaults(path: Path) -> None:
    _require(path.exists(), f"missing bundle file: {path}")
    _require(path.read_text() == EXPECTED_DEFAULTS, f"{path} must match the canonical coilyco defaults bundle")


def _validate_release_tar_members(path: Path) -> None:
    _require(path.exists(), f"missing release workflow: {path}")
    text = path.read_text()
    _require(EXPECTED_TAR_MEMBER in text, f"{path} must package {EXPECTED_TAR_MEMBER} into ward-specs")


def main() -> int:
    if not sys.argv[1:]:
        _validate_defaults(DEFAULTS_PATH)
        _validate_release_tar_members(RELEASE_PATH)
        return 0

    for arg in sys.argv[1:]:
        if arg == "--defaults-only":
            _validate_defaults(DEFAULTS_PATH)
        elif arg == "--release-only":
            _validate_release_tar_members(RELEASE_PATH)
        else:
            fail(f"unknown argument {arg!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

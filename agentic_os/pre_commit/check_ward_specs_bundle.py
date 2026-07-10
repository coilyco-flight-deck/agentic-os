"""Validate the coilyco ward-specs bundle.

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
        repo "coilyco-flight-deck/cli-guard" workflow="pull-requests-and-merge"
        repo "coilyco-flight-deck/ward" workflow="pull-requests-and-merge"
        repo "coilyco-flight-deck/agentic-os" workflow="pull-requests-and-merge"
    }
}

repo-authority default=forgejo {
    trusted-owner coilysiren
    trusted-owner coilyco-bridge
    trusted-owner coilyco-flight-deck
    trusted-owner coilyco-gaming

    repo "coilysiren/*" forge=github
    repo "coilyco-bridge/*" forge=forgejo
    repo "coilyco-flight-deck/*" forge=forgejo
    repo "coilyco-gaming/*" forge=forgejo
}
"""
EXPECTED_TAR_MEMBERS = (
    "./forgejo-actions-logs.sh",
    "./forgejo-actions-rerun-failed-jobs.sh",
    "./forgejo-actions-rerun.sh",
    "./forgejo.swagger.lock.json",
    "./specverb.lock",
    "./ward-kdl.aws.guardfile.kdl",
    "./ward-kdl.defaults.kdl",
    "./ward-kdl.fleet.kdl",
    "./ward-kdl.forgejo.admin.guardfile.kdl",
    "./ward-kdl.forgejo.guardfile.kdl",
    "./ward-kdl.forgejo.rerun.guardfile.kdl",
    "./ward-kdl.forgejo.read.guardfile.kdl",
    "./ward-kdl.forgejo.logs.guardfile.kdl",
    "./ward-kdl.forgejo.write.guardfile.kdl",
    "./ward-kdl.kubectl.guardfile.kdl",
    "./ward-kdl.roles.kdl",
)
REMOVED_TAR_MEMBERS = (
    "./glitchtip.openapi.lock.json",
    "./signoz.openapi.lock.json",
    "./ward-kdl.forgejo.actions.guardfile.kdl",
    "./ward-kdl.ollama.guardfile.kdl",
    "./ward-kdl.signoz.guardfile.kdl",
)


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
    for member in EXPECTED_TAR_MEMBERS:
        _require(member in text, f"{path} must package {member} into ward-specs")
    for member in REMOVED_TAR_MEMBERS:
        _require(member not in text, f"{path} must not package removed ward-specs member {member}")


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

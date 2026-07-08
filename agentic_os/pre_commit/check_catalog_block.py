#!/usr/bin/env python3
"""pre-commit hook: assert this repo's catalog config has a top-level `catalog:` block.

Reads the repo's `.ward/ward.yaml` catalog config. It must exist and
carry the block.

Schema and rollout: see docs/ward-specs.md and docs/features-release-tooling.md.

Required keys inside `catalog:`:
    dependsOn.

`dependsOn` is the only load-bearing key - it is the substrate auto-mount
manifest ward reads at agent launch (`ward/cmd/ward/agent_context.go`).
Everything else in the block is optional graph-metadata: `description` is an
optional label, and `kind`, `type`, `system`, `owner`, `lifecycle` are the
Backstage-vocab keys retired fleet-wide. They may still appear and are ignored
by this hook; the catalog-graph builder no longer reads them.

`dependsOn` must be a list. Trivial repos (e.g. a single .gitignore) still
declare it, using `[]` for empty rather than omitting the key. Empty is
fine. Missing is not.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn

from agentic_os.config import is_enabled

HOOK_ID = "catalog-block-present"

try:
    import yaml  # type: ignore[import-untyped, unused-ignore]
except ImportError:  # pragma: no cover
    print(
        "check-catalog-block: PyYAML not available.\n"
        "  Short-term fix: pip install pyyaml\n"
        "  Durable fix: this hook is running under `language: system` against a host\n"
        "  python that lacks pyyaml. Migrate the repo's .pre-commit-config.yaml entry\n"
        "  for catalog-block-present to the uv-managed shape (`language: python` +\n"
        "  `additional_dependencies: [pyyaml]`). Canonical block:\n"
        "    agentic-os-kai/scripts/apply-catalog-block-hook.py (MANAGED_BLOCK).\n"
        "  Refresh fleet-wide with: ward exec apply-catalog-block-hook\n"
        "  Tracker: docs/ward-specs.md",
        file=sys.stderr,
    )
    sys.exit(1)


REQUIRED_KEYS = ("dependsOn",)
LIST_KEYS = ("dependsOn",)
TRACKER = "docs/ward-specs.md"


def fail(msg: str) -> NoReturn:
    print(f"check-catalog-block: {msg}")
    print(f"  see {TRACKER} for schema")
    sys.exit(1)


CONFIG_PATH = Path(".ward/ward.yaml")


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    path = CONFIG_PATH if CONFIG_PATH.exists() else None
    if path is None:
        fail("no catalog config found. Every coilysiren/* repo needs .ward/ward.yaml.")

    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        fail(f"{path} is not valid YAML: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} top level must be a mapping")

    catalog = data.get("catalog")
    if not isinstance(catalog, dict):
        fail(f"{path} missing top-level `catalog:` block")

    missing = [k for k in REQUIRED_KEYS if k not in catalog]
    if missing:
        fail(
            "catalog block missing required keys: "
            + ", ".join(missing)
            + ". Trivial repos still declare them (use [] for list keys)."
        )

    for k in LIST_KEYS:
        if not isinstance(catalog[k], list):
            fail(f"catalog.{k} must be a list (use [] for empty)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

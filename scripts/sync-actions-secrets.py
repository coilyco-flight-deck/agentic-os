#!/usr/bin/env python3
"""Sync Forgejo Actions secrets from their SSM sources of truth.

Repo Actions secrets (Telegram alert credentials, promote/release PAT, and
package-repository writers) are write-only in Forgejo, so drift shows up as
silently-dead alert or publication steps. This makes the mapping explicit and
re-applying it one verb: `ward exec sync-actions-secrets` (add `-- --dry-run`
to preview).

Values never touch disk or argv: read from SSM with the AWS CLI, PUT straight
to the Forgejo secrets API, authenticated by the /forgejo/api-token PAT.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

FORGEJO_BASE = "https://forgejo.coilysiren.me/api/v1"
OWNER = "coilyco-flight-deck"
API_TOKEN_PARAM = "/forgejo/api-token"
TELEGRAM_DEFAULTS_PATH = (
    Path(__file__).resolve().parent.parent
    / "actions"
    / "telegram-alert"
    / "defaults.json"
)


def load_secret_sources(path: Path) -> dict[str, str]:
    """Load Actions-secret to SSM-parameter mappings from an action manifest."""
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["schema-version"] != 1:
            raise ValueError("unsupported schema-version")
        secrets = manifest["secrets"]
        sources = {
            value["actions-secret"]: value["ssm-parameter"]
            for value in secrets.values()
        }
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid action defaults manifest {path}: {exc}") from exc
    if not sources or any(
        not name or not parameter.startswith("/")
        for name, parameter in sources.items()
    ):
        raise SystemExit(f"invalid action secret sources in {path}")
    return sources


TELEGRAM_SECRET_SOURCES = load_secret_sources(TELEGRAM_DEFAULTS_PATH)

# repo -> secret name -> SSM parameter (see SSM.md in agentic-os-kai).
# Release and package writers use their separately rotated SSM token family.
MAPPING: dict[str, dict[str, str]] = {
    "agentic-os": {
        **TELEGRAM_SECRET_SOURCES,
        "CI_RELEASE_TOKEN": "/forgejo/coilyco-ops/ci-release-token",
        "TAP_WRITE_TOKEN": "/forgejo/coilyco-ops/tap-bump-token",
        "SCOOP_WRITE_TOKEN": "/forgejo/coilyco-ops/scoop-write-token",
    },
    "ward": {
        **TELEGRAM_SECRET_SOURCES,
        "CI_RELEASE_TOKEN": "/forgejo/coilyco-ops/ci-release-token",
    },
    "cli-guard": {
        **TELEGRAM_SECRET_SOURCES,
        "CI_RELEASE_TOKEN": "/forgejo/coilyco-ops/ci-release-token",
    },
}


def ssm_get(name: str) -> str:
    out = subprocess.run(
        [
            "aws", "ssm", "get-parameter", "--name", name, "--with-decryption",
            "--query", "Parameter.Value", "--output", "text",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    value = out.stdout.strip()
    if not value:
        raise SystemExit(f"ssm parameter {name} resolved empty")
    return value


def put_secret(token: str, repo: str, name: str, value: str) -> None:
    url = f"{FORGEJO_BASE}/repos/{OWNER}/{repo}/actions/secrets/{name}"
    body = json.dumps({"data": value}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    args = parser.parse_args()

    plan = [
        (repo, name, param)
        for repo, secrets in MAPPING.items()
        for name, param in secrets.items()
    ]
    for repo, name, param in plan:
        print(f"{OWNER}/{repo}: {name} <- ssm {param}")
    if args.dry_run:
        return 0

    token = os.environ.get("FORGEJO_ADMIN_TOKEN") or ssm_get(API_TOKEN_PARAM)
    for repo, name, param in plan:
        put_secret(token, repo, name, ssm_get(param))
        print(f"{OWNER}/{repo}: {name} set")
    return 0


if __name__ == "__main__":
    sys.exit(main())

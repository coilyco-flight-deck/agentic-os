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

FORGEJO_BASE = "https://forgejo.coilysiren.me/api/v1"
OWNER = "coilyco-flight-deck"
API_TOKEN_PARAM = "/forgejo/api-token"

# repo -> secret name -> SSM parameter (see SSM.md in agentic-os-kai).
# Release and package writers use their separately rotated SSM token family.
MAPPING: dict[str, dict[str, str]] = {
    "agentic-os": {
        "TELEGRAM_BOT_TOKEN": "/coilysiren/telegram/bot-token",
        "TELEGRAM_RED_CHAT_ID": "/coilysiren/telegram/red-chat-id",
        "CI_RELEASE_TOKEN": "/forgejo/ci-release-token",
        "TAP_WRITE_TOKEN": "/forgejo/tap-bump-token",
        "SCOOP_WRITE_TOKEN": "/forgejo/scoop-write-token",
    },
    "ward": {
        "TELEGRAM_BOT_TOKEN": "/coilysiren/telegram/bot-token",
        "TELEGRAM_RED_CHAT_ID": "/coilysiren/telegram/red-chat-id",
        "CI_RELEASE_TOKEN": "/forgejo/ci-release-token",
    },
    "cli-guard": {
        "TELEGRAM_BOT_TOKEN": "/coilysiren/telegram/bot-token",
        "TELEGRAM_RED_CHAT_ID": "/coilysiren/telegram/red-chat-id",
        "CI_RELEASE_TOKEN": "/forgejo/ci-release-token",
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

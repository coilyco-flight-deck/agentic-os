#!/usr/bin/env python3
"""Remint the two-stage promote PAT (CI_RELEASE_TOKEN) on the coilyco-ops bot.

The promote push needs read:user alongside write:repository: without it Forgejo
cannot attribute the push and silently enqueues no release run (ward#1117). Token
endpoints accept basic auth only and only the bot's password is in SSM, so the
PAT is minted on the bot. Values stay in-process, never disk or argv. Follow with
`just sync-actions-secrets`.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request

import boto3

from agentic_os import shared_ssl_context

FORGEJO_BASE = "https://forgejo.coilysiren.me/api/v1"
BOT_USER = "coilyco-ops"
TOKEN_NAME = "ci-release-token"
SCOPES = ["write:repository", "read:user"]
PASSWORD_PARAM = "/forgejo/coilyco-ops/password"
TARGET_PARAM = "/forgejo/coilyco-ops/ci-release-token"


def api(method: str, path: str, auth: str, body: dict | None = None) -> tuple[int, object]:
    request = urllib.request.Request(
        f"{FORGEJO_BASE}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=30, context=shared_ssl_context()
        ) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {path} failed: {error.code} {detail}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    args = parser.parse_args()

    print(f"mint {TOKEN_NAME} on {BOT_USER} with scopes {SCOPES}, stash to ssm {TARGET_PARAM}")
    if args.dry_run:
        return 0

    ssm = boto3.client("ssm")
    password = ssm.get_parameter(Name=PASSWORD_PARAM, WithDecryption=True)["Parameter"]["Value"]
    basic = "Basic " + base64.b64encode(f"{BOT_USER}:{password}".encode()).decode()

    _, existing = api("GET", f"/users/{BOT_USER}/tokens", basic)
    for token in existing or []:
        if token.get("name") == TOKEN_NAME:
            api("DELETE", f"/users/{BOT_USER}/tokens/{token['id']}", basic)
            print(f"deleted prior token {TOKEN_NAME} (id {token['id']})")

    _, minted = api(
        "POST",
        f"/users/{BOT_USER}/tokens",
        basic,
        {"name": TOKEN_NAME, "scopes": SCOPES},
    )
    value = minted.get("sha1", "")
    if not value:
        raise SystemExit("token create returned no value")

    _, whoami = api("GET", "/user", f"token {value}")
    login = (whoami or {}).get("login")
    if login != BOT_USER:
        raise SystemExit(f"attribution check failed: GET /user returned {login!r}")
    print(f"minted; GET /user attributes as {login} (read:user verified)")

    ssm.put_parameter(Name=TARGET_PARAM, Value=value, Type="SecureString", Overwrite=True)
    print(f"ssm {TARGET_PARAM} updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

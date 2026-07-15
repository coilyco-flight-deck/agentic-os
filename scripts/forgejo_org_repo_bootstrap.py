#!/usr/bin/env python3
"""Create or reconcile an org repo on Forgejo for a GitHub profile mirror."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "https://forgejo.coilysiren.me"
DEFAULT_DEFAULT_BRANCH = "main"
ADMIN_TOKEN_PARAM = "/forgejo/api-token"


@dataclass(frozen=True)
class RepoSpec:
    org: str
    name: str
    description: str
    default_branch: str
    private: bool


def _forgejo_base_url() -> str:
    return os.environ.get("FORGEJO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _load_token() -> str:
    token = os.environ.get("FORGEJO_TOKEN")
    if token:
        return token.strip()

    proc = subprocess.run(
        [
            "ward_ssm",
            "get-parameter",
            "--name",
            ADMIN_TOKEN_PARAM,
            "--with-decryption",
            "--query",
            "Parameter.Value",
            "--output",
            "text",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    token = proc.stdout.strip()
    if not token:
        raise RuntimeError(f"{ADMIN_TOKEN_PARAM} returned an empty token")
    return token


def _request_json(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed: Any = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def _repo_url(base_url: str, org: str, name: str) -> str:
    path = urllib.parse.quote(org, safe="")
    repo = urllib.parse.quote(name, safe="")
    return f"{base_url}/api/v1/repos/{path}/{repo}"


def _create_url(base_url: str, org: str) -> str:
    return f"{base_url}/api/v1/orgs/{urllib.parse.quote(org, safe='')}/repos"


def _create_payload(spec: RepoSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "description": spec.description,
        "private": spec.private,
        "default_branch": spec.default_branch,
        "auto_init": False,
    }


def _patch_payload(spec: RepoSpec) -> dict[str, Any]:
    return {
        "description": spec.description,
        "private": spec.private,
        "default_branch": spec.default_branch,
    }


def bootstrap_repo(spec: RepoSpec, token: str, base_url: str) -> tuple[str, Any]:
    repo_url = _repo_url(base_url, spec.org, spec.name)
    create_url = _create_url(base_url, spec.org)

    status, data = _request_json("GET", repo_url, token)
    created = False
    if status == 404:
        status, data = _request_json("POST", create_url, token, _create_payload(spec))
        if status not in (200, 201):
            raise RuntimeError(f"repo create failed with HTTP {status}: {data}")
        created = True
    elif status != 200:
        raise RuntimeError(f"repo lookup failed with HTTP {status}: {data}")

    status, data = _request_json("PATCH", repo_url, token, _patch_payload(spec))
    if status not in (200, 201):
        raise RuntimeError(f"repo update failed with HTTP {status}: {data}")

    action = "created" if created else "updated"
    return action, data


def _parse_args(argv: list[str]) -> RepoSpec:
    parser = argparse.ArgumentParser(
        description="Create or reconcile an org repo on Forgejo."
    )
    parser.add_argument("org", help="Forgejo organization slug")
    parser.add_argument("repo", help="repository name")
    parser.add_argument(
        "--description",
        required=True,
        help="repository description to set or refresh",
    )
    parser.add_argument(
        "--default-branch",
        default=DEFAULT_DEFAULT_BRANCH,
        help="default branch to set on create",
    )
    visibility = parser.add_mutually_exclusive_group()
    visibility.add_argument(
        "--private",
        action="store_true",
        help="create or keep the repo private",
    )
    visibility.add_argument(
        "--public",
        action="store_true",
        help="create or keep the repo public",
    )
    ns = parser.parse_args(argv)
    private = True if ns.private else False
    if not ns.private and not ns.public:
        private = False
    return RepoSpec(
        org=ns.org,
        name=ns.repo,
        description=ns.description,
        default_branch=ns.default_branch,
        private=private,
    )


def main(argv: list[str] | None = None) -> int:
    spec = _parse_args(sys.argv[1:] if argv is None else argv)
    token = _load_token()
    action, data = bootstrap_repo(spec, token, _forgejo_base_url())
    html_url = data.get("html_url") if isinstance(data, dict) else None
    suffix = f" ({html_url})" if html_url else ""
    print(f"{action} {spec.org}/{spec.name}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

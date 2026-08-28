"""Read and extend a Netlify site's domain aliases without dropping any.

The API replaces `domain_aliases` wholesale on update, and the caller knows
only what it wants to add, so every write here is a read-modify-write of the
full list. See ../../../docs/aosguard.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.netlify.com/api/v1"
TIMEOUT = 30


def _request(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "aosguard-netlify",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def _token() -> str:
    token = os.environ.get("NETLIFY_AUTH_TOKEN", "").strip()
    if not token:
        raise SystemExit("netlify: NETLIFY_AUTH_TOKEN is empty (fail-closed)")
    return token


def _render(site: dict) -> None:
    print(f"site={site.get('name')}")
    print(f"custom_domain={site.get('custom_domain')}")
    for alias in site.get("domain_aliases") or []:
        print(f"alias={alias}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="netlify")
    parser.add_argument("action", choices=("show", "add"))
    parser.add_argument("--site", required=True)
    parser.add_argument("--alias", action="append", default=[])
    args = parser.parse_args(argv)

    token = _token()
    site = _request("GET", f"/sites/{args.site}", token)
    if args.action == "show":
        _render(site)
        return 0

    if not args.alias:
        raise SystemExit("netlify: add needs at least one --alias (fail-closed)")

    current = list(site.get("domain_aliases") or [])
    primary = {site.get("custom_domain"), site.get("name")}
    merged = list(current)
    for alias in args.alias:
        if alias in primary:
            raise SystemExit(f"netlify: {alias} is the site's primary domain (fail-closed)")
        if alias not in merged:
            merged.append(alias)
    if merged == current:
        print("no change; every alias is already present")
        _render(site)
        return 0

    # One update for every alias: each write re-issues the certificate covering
    # the primary domain too, so batching is a safety property, not tidiness.
    print(f"adding {len(merged) - len(current)} alias(es) to {len(current)} existing")
    updated = _request("PATCH", f"/sites/{args.site}", token, {"domain_aliases": merged})
    _render(updated)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as error:
        print(f"netlify: {error.code} {error.reason}", file=sys.stderr)
        raise SystemExit(1) from error
    except urllib.error.URLError as error:
        # A traceback here reads as a script bug rather than an unreachable API.
        print(f"netlify: cannot reach {API}: {error.reason}", file=sys.stderr)
        raise SystemExit(1) from error

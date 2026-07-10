"""Forgejo Actions rerun bridge for status-target rerun verbs."""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://forgejo.coilysiren.me"

MODE_TO_SUFFIX = {
    "rerun": "rerun",
    "rerun-failed-jobs": "rerun-failed-jobs",
}


def _http_post(url: str, token: str) -> bytes:
    request = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.read()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="actions rerun",
        description="Rerun a Forgejo Actions workflow run by its visible run id.",
    )
    parser.add_argument("mode", choices=sorted(MODE_TO_SUFFIX))
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("run_id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    token = os.environ.get("FORGEJO_TOKEN")
    if not token:
        print("FORGEJO_TOKEN is required", file=sys.stderr)
        return 1

    base_url = os.environ.get("FORGEJO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    suffix = MODE_TO_SUFFIX[args.mode]
    url = (
        f"{base_url}/api/v1/repos/{args.owner}/{args.repo}/actions/runs/"
        f"{args.run_id}/{suffix}"
    )
    try:
        payload = _http_post(url, token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(
                "Forgejo returned 404 for the rerun route. "
                f"target_url={url}",
                file=sys.stderr,
            )
            return 65
        raise
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 65

    if payload:
        sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

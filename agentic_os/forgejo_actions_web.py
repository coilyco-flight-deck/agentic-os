"""Shared helpers for Forgejo Actions web UI bridges."""

from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.request

DEFAULT_USERNAME = "coilyco-ops"
INITIAL_POST_RE = re.compile(
    r'data-initial-post-response="(?P<payload>.*?)"\s*data-initial-artifacts-response=',
    re.DOTALL,
)


class ForgejoActionsWebError(RuntimeError):
    """The web UI bridge could not resolve the requested page payload."""


def _authorization_value(token: str, *, auth_scheme: str) -> str:
    username = os.environ.get("FORGEJO_USERNAME", DEFAULT_USERNAME)
    if auth_scheme == "basic":
        encoded = base64.b64encode(f"{username}:{token}".encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"
    if auth_scheme == "token":
        return f"token {token}"
    raise ValueError(f"unsupported Forgejo auth scheme: {auth_scheme}")


def request(
    url: str,
    token: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    auth_scheme: str = "basic",
) -> bytes:
    headers = {"Authorization": _authorization_value(token, auth_scheme=auth_scheme)}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req) as response:
        return response.read()


def extract_initial_post_response(page_html: str, *, page_url: str) -> dict:
    payload_match = INITIAL_POST_RE.search(page_html)
    if not payload_match:
        raise ForgejoActionsWebError(
            f"could not find the initial job payload in the Forgejo page. target_url={page_url}"
        )
    try:
        return json.loads(html.unescape(payload_match.group("payload")))
    except json.JSONDecodeError as exc:
        raise ForgejoActionsWebError(
            f"Forgejo returned an unreadable page payload. target_url={page_url}"
        ) from exc

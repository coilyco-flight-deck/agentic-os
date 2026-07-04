"""Resolve the GlitchTip DSN, from SSM by default, and parse it.

Per the Sentry-DSN-in-SSM rule the GlitchTip DSN lives in an SSM parameter
(default ``/sentry-dsn/tool-failures``, recorded in SSM.md), read via the ward
operator verb rather than a boto3 dependency. The read is cached on first
success and fail-soft: any error (missing param, expired creds, no ward on
PATH) returns ``None`` so the buffer keeps accumulating instead of crashing a
producer-adjacent timer. ``TOOL_FAILURES_DSN`` short-circuits SSM for tests and
for the DSN-pluggable half that lands before the project exists.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_SSM_PATH = "/sentry-dsn/tool-failures"

_cache: dict[str, str | None] = {}


def ssm_path() -> str:
    return os.environ.get("TOOL_FAILURES_DSN_SSM_PATH") or DEFAULT_SSM_PATH


def _read_ssm(path: str) -> str | None:
    """Fetch an SSM parameter value via ``ward ops aws ssm``. None on any error."""
    try:
        proc = subprocess.run(
            [
                "ward",
                "ops",
                "aws",
                "ssm",
                "get-parameter",
                "--name",
                path,
                "--with-decryption",
                "--query",
                "Parameter.Value",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def resolve_dsn(*, use_cache: bool = True) -> str | None:
    """The GlitchTip DSN, or ``None`` when unavailable (fail-soft).

    ``TOOL_FAILURES_DSN`` wins; otherwise the SSM parameter is read once and
    cached under its path. A caching miss (``None``) is also cached so a run
    with no DSN does not re-shell SSM per file.
    """
    direct = os.environ.get("TOOL_FAILURES_DSN")
    if direct:
        return direct.strip()
    path = ssm_path()
    if use_cache and path in _cache:
        return _cache[path]
    value = _read_ssm(path)
    _cache[path] = value
    return value


def clear_cache() -> None:
    _cache.clear()


@dataclass(frozen=True)
class Dsn:
    """A parsed Sentry/GlitchTip DSN and its derived envelope endpoint."""

    public_key: str
    envelope_url: str

    @property
    def auth_header(self) -> str:
        return (
            "Sentry sentry_version=7, "
            "sentry_client=agentic-os-tool-failures/1.0, "
            f"sentry_key={self.public_key}"
        )


def parse_dsn(dsn: str) -> Dsn:
    """Parse ``<scheme>://<key>@<host>[:port]/<path><project_id>`` into a Dsn.

    Raises ``ValueError`` on a DSN missing the public key or project id.
    """
    parts = urlsplit(dsn.strip())
    if not parts.scheme or not parts.hostname:
        raise ValueError(f"DSN missing scheme/host: {dsn!r}")
    if not parts.username:
        raise ValueError(f"DSN missing public key: {dsn!r}")
    segments = [s for s in parts.path.split("/") if s]
    if not segments:
        raise ValueError(f"DSN missing project id: {dsn!r}")
    project_id = segments[-1]
    prefix = "/".join(segments[:-1])
    host = parts.hostname
    if parts.port:
        host = f"{host}:{parts.port}"
    base = f"{parts.scheme}://{host}"
    path = (
        f"/{prefix}/api/{project_id}/envelope/"
        if prefix
        else f"/api/{project_id}/envelope/"
    )
    return Dsn(public_key=parts.username, envelope_url=base + path)

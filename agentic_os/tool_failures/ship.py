"""Drain the failure-record buffer to GlitchTip. CLI entrypoint + orchestration.

``ward exec ship-tool-failures`` (or a SessionEnd hook / timer) runs this
out-of-band from the producers, never on a hot path. It resolves the DSN
(fail-soft), then for each per-repo buffer reads past the watermark, gates on
genuine failures, and POSTs one fingerprinted envelope per failure, advancing
the watermark line-by-line so a re-run neither re-ships an accepted event nor
loses one after a mid-file network error.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import buffer, dsn as dsn_mod, envelope


@dataclass
class ShipSummary:
    """What a drain run did, for the terminal line and the exit code."""

    shipped: int = 0
    skipped: int = 0
    failed: int = 0
    files: int = 0
    dsn_present: bool = False
    dry_run: bool = False
    errors: list[str] = field(default_factory=list)

    def line(self) -> str:
        mode = (
            "dry-run" if self.dry_run else ("shipped" if self.dsn_present else "no-dsn")
        )
        return (
            f"tool-failures ship [{mode}]: {self.shipped} shipped, "
            f"{self.skipped} skipped, {self.failed} failed "
            f"across {self.files} buffer file(s)"
        )


def _post_envelope(url: str, auth_header: str, body: bytes, *, timeout: float) -> None:
    """POST one envelope. Raises urllib.error on a non-2xx / transport error."""
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-sentry-envelope",
            "X-Sentry-Auth": auth_header,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status >= 300:
            raise urllib.error.HTTPError(
                url, resp.status, "unexpected status", resp.headers, None
            )


def _ship_file(
    path: Path,
    offset: int,
    parsed: dsn_mod.Dsn | None,
    summary: ShipSummary,
    *,
    dry_run: bool,
    timeout: float,
) -> int:
    """Drain one buffer file from `offset`. Returns the new watermark offset."""
    watermark = offset
    for record, end in buffer.drain_records(path, offset):
        if record is None or not buffer.is_genuine(record):
            summary.skipped += 1
            watermark = end
            continue
        event = envelope.build_event(record)
        if dry_run or parsed is None:
            summary.shipped += 1
            watermark = end
            continue
        try:
            _post_envelope(
                parsed.envelope_url,
                parsed.auth_header,
                envelope.build_envelope(event),
                timeout=timeout,
            )
        except (urllib.error.URLError, OSError) as exc:
            summary.failed += 1
            summary.errors.append(f"{path.name}: {exc}")
            break
        summary.shipped += 1
        watermark = end
    return watermark


def ship(
    *,
    directory: Path | None = None,
    repo: str | None = None,
    dry_run: bool = False,
    timeout: float = 15.0,
) -> ShipSummary:
    """Drain every (or one) per-repo buffer to GlitchTip and return a summary.

    Fail-soft: when no DSN resolves (and not a dry run) the watermarks are left
    untouched so the buffer keeps accumulating until the DSN exists.
    """
    directory = directory or buffer.buffer_dir()
    summary = ShipSummary(dry_run=dry_run)

    parsed: dsn_mod.Dsn | None = None
    if not dry_run:
        raw = dsn_mod.resolve_dsn()
        if raw:
            try:
                parsed = dsn_mod.parse_dsn(raw)
                summary.dsn_present = True
            except ValueError as exc:
                summary.errors.append(f"invalid DSN: {exc}")
                return summary
        else:
            summary.errors.append("no DSN resolved; buffer left to accumulate")
            return summary

    files = buffer.buffer_files(directory)
    if repo is not None:
        files = [f for f in files if buffer.repo_slug(f) == repo]
    summary.files = len(files)
    if not files:
        return summary

    watermarks = buffer.load_watermarks(directory)
    for path in files:
        key = path.name
        new_offset = _ship_file(
            path,
            watermarks.get(key, 0),
            parsed,
            summary,
            dry_run=dry_run,
            timeout=timeout,
        )
        watermarks[key] = new_offset
    if not dry_run:
        buffer.save_watermarks(directory, watermarks)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ship-tool-failures",
        description="Drain the tool-use failure-record buffer to GlitchTip.",
    )
    parser.add_argument(
        "--buffer-dir", type=Path, default=None, help="override the buffer dir"
    )
    parser.add_argument(
        "--repo", default=None, help="drain only this repo slug's buffer"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build events and preview counts without a DSN, POST, or watermark write",
    )
    parser.add_argument(
        "--timeout", type=float, default=15.0, help="per-POST timeout seconds"
    )
    args = parser.parse_args(argv)

    summary = ship(
        directory=args.buffer_dir,
        repo=args.repo,
        dry_run=args.dry_run,
        timeout=args.timeout,
    )
    print(summary.line())
    for err in summary.errors:
        print(f"  note: {err}", file=sys.stderr)
    # Fail-soft: a missing DSN is expected (exit 0); only real POST failures fail.
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

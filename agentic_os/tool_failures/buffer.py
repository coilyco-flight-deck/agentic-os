"""Read the per-repo failure-record buffer and track a drained watermark.

The buffer directory holds one append-only ``<repo-slug>.jsonl`` per repo plus
this shipper's own ``.ship-watermarks.json``. Draining reads only the bytes
appended since the last recorded byte-offset, so a re-drain is idempotent and a
file shorter than its watermark (rotation/truncation) resets to zero. Records
whose classifier already marked them ``expected`` (benign non-zero exits) are
dropped here - the shipper is the final genuine-failure gate.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

WATERMARK_FILENAME = ".ship-watermarks.json"


def buffer_dir() -> Path:
    """Buffer directory. ``TOOL_FAILURES_BUFFER_DIR`` overrides for tests/hosts."""
    override = os.environ.get("TOOL_FAILURES_BUFFER_DIR")
    if override:
        return Path(override)
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    return Path(cache) / "agentic-os" / "tool-failures"


def buffer_files(directory: Path) -> list[Path]:
    """Every ``<repo-slug>.jsonl`` buffer in `directory`, sorted, dotfiles out."""
    if not directory.is_dir():
        return []
    return sorted(
        p
        for p in directory.glob("*.jsonl")
        if not p.name.startswith(".") and p.is_file()
    )


def repo_slug(path: Path) -> str:
    """Repo slug a buffer file belongs to (its stem)."""
    return path.stem


def is_genuine(record: dict) -> bool:
    """True when `record` is a genuine failure worth shipping.

    Drops records the upstream classifier flagged ``expected`` (benign no-match
    grep, false ``test``, ``|| true``) and records missing the load-bearing
    fingerprint/failure_class fields.
    """
    if not isinstance(record, dict):
        return False
    if record.get("expected"):
        return False
    return bool(record.get("fingerprint")) and bool(record.get("failure_class"))


def watermark_path(directory: Path) -> Path:
    return directory / WATERMARK_FILENAME


def load_watermarks(directory: Path) -> dict[str, int]:
    """Per-file byte offsets already shipped. Missing/corrupt reads as empty."""
    path = watermark_path(directory)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: int(v) for k, v in data.items() if isinstance(v, (int, float))}


def save_watermarks(directory: Path, watermarks: dict[str, int]) -> None:
    """Persist watermarks atomically (temp file + replace)."""
    directory.mkdir(parents=True, exist_ok=True)
    path = watermark_path(directory)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(watermarks, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def drain_records(path: Path, offset: int) -> Iterator[tuple[dict | None, int]]:
    """Yield ``(record, end_offset)`` for each line appended after `offset`.

    `record` is the parsed JSON object, or ``None`` for an unparseable line
    (the caller still advances past it). `end_offset` is the byte position just
    after that line, the value to persist once the line is handled. A file
    shorter than `offset` (rotation) is re-read from the start.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return
    start = 0 if offset > size else offset
    with path.open("rb") as fh:
        fh.seek(start)
        pos = start
        for raw in fh:
            pos += len(raw)
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                yield None, pos
                continue
            try:
                record = json.loads(text)
            except ValueError:
                yield None, pos
                continue
            yield record, pos

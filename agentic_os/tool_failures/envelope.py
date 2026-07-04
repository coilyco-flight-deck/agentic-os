"""Turn a schema-v1 failure-record into a Sentry-protocol event and envelope.

Grouping is the whole point: the Sentry ``fingerprint`` is set to the record's
own ``fingerprint`` so a flood of identical failures collapses to one GlitchTip
issue with an accurate event count. The event ``message`` stays a closed-set
string (``<harness> tool failure: <failure_class>``) per the o11y
high-cardinality rule - volatile detail (stderr excerpt, exit code, session id)
rides in tags and ``extra``, never in the title.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

# Fields promoted to their own event slots; everything else falls to `extra`.
_TAG_FIELDS = ("harness", "failure_class", "repo", "source", "schema_title", "tool")
_PROMOTED = {"ts", "fingerprint", "detail", *_TAG_FIELDS}


def _iso_timestamp(record: dict) -> str:
    ts = record.get("ts")
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return datetime.now(tz=timezone.utc).isoformat()


def build_event(record: dict) -> dict:
    """Build a Sentry event dict from a schema-v1 failure-record."""
    harness = str(record.get("harness", "unknown"))
    failure_class = str(record.get("failure_class", "unknown"))
    tags = {k: str(record[k]) for k in _TAG_FIELDS if record.get(k) is not None}
    extra = {k: v for k, v in record.items() if k not in _PROMOTED}
    if record.get("detail"):
        extra["detail"] = record["detail"]
    event = {
        "event_id": uuid.uuid4().hex,
        "timestamp": _iso_timestamp(record),
        "platform": "other",
        "level": "error",
        "logger": "agentic-os.tool-failures",
        "message": f"{harness} tool failure: {failure_class}",
        "fingerprint": [str(record["fingerprint"])],
        "tags": tags,
    }
    if extra:
        event["extra"] = extra
    return event


def build_envelope(event: dict) -> bytes:
    """Frame `event` as a single-item Sentry envelope body."""
    payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
    header = json.dumps({"event_id": event["event_id"]}).encode("utf-8")
    item_header = json.dumps(
        {"type": "event", "content_type": "application/json", "length": len(payload)}
    ).encode("utf-8")
    return b"\n".join((header, item_header, payload)) + b"\n"

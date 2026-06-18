"""Tests for goose_json.ask() failure instrumentation (failure-record schema v1).

Every ask() failure path must write one classified failure-record to the per-repo
buffer instead of discarding `.returncode` / `.stderr`, while the success path and
the dict|None return contract stay unchanged. See docs/goose-triage.md, agentic-os#248.
"""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import goose_json  # noqa: E402

SCHEMA = {"type": "object", "required": ["score"],
          "properties": {"score": {"type": "integer"}}}


def _envelope(obj) -> str:
    """A Goose --output-format json envelope carrying one assistant JSON message."""
    return json.dumps({"messages": [
        {"role": "assistant", "content": [{"text": json.dumps(obj)}]}]})


def _proc(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


@pytest.fixture
def buffer(tmp_path, monkeypatch):
    """Redirect the failure buffer into a tmp dir and pin the repo slug."""
    monkeypatch.setattr(goose_json, "FAILURE_DIR", tmp_path)
    monkeypatch.setattr(goose_json, "_REPO_SLUG_CACHE", ["owner/repo"])
    return tmp_path


def _records(buffer: Path, repo="owner-repo") -> list[dict]:
    path = buffer / f"{repo}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_success_returns_object_and_writes_no_record(buffer, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(stdout=_envelope({"score": 7})))
    assert goose_json.ask("p", SCHEMA) == {"score": 7}
    assert _records(buffer) == []


def test_timeout_records_then_exhausted(buffer, monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="goose", timeout=120)
    monkeypatch.setattr(subprocess, "run", boom)
    assert goose_json.ask("p", SCHEMA, retries=2) is None
    recs = _records(buffer)
    classes = [r["failure_class"] for r in recs]
    assert classes == ["timeout", "timeout", "exhausted_retries"]
    assert all(r["exit_code"] is None for r in recs)
    assert recs[0]["attempt"] == 0 and recs[1]["attempt"] == 1


def test_nonzero_exit_keeps_stderr_and_returncode(buffer, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(stdout="", stderr="provider 503\n", returncode=1))
    assert goose_json.ask("p", SCHEMA, retries=1) is None
    recs = _records(buffer)
    assert recs[0]["failure_class"] == "nonzero_exit"
    assert recs[0]["exit_code"] == 1
    assert "provider 503" in recs[0]["stderr_excerpt"]


def test_bad_envelope_classified(buffer, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(stdout="not json at all", returncode=0))
    assert goose_json.ask("p", SCHEMA, retries=1) is None
    assert _records(buffer)[0]["failure_class"] == "bad_envelope"


def test_no_schema_valid_message_classified(buffer, monkeypatch):
    # Valid envelope, but the assistant message omits the required "score" key.
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(stdout=_envelope({"nope": 1}), returncode=0))
    assert goose_json.ask("p", SCHEMA, retries=1) is None
    assert _records(buffer)[0]["failure_class"] == "no_schema_valid_message"


def test_record_carries_full_schema_v1(buffer, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(stderr="boom", returncode=2))
    goose_json.ask("p", SCHEMA, retries=1, label="urgency")
    rec = _records(buffer)[0]
    for field in ("ts", "harness", "source", "repo", "failure_class", "schema_title",
                  "exit_code", "attempt", "stderr_excerpt", "detail", "fingerprint"):
        assert field in rec, field
    assert rec["harness"] == "goose"
    assert rec["source"] == "goose_json.ask"
    assert rec["repo"] == "owner/repo"
    assert rec["schema_title"] == "urgency"


def test_label_overrides_schema_title_in_path_and_record(buffer, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(returncode=1, stderr="x"))
    goose_json.ask("p", SCHEMA, retries=1, repo="a/b", label="mode")
    recs = _records(buffer, repo="a-b")
    assert recs and recs[0]["schema_title"] == "mode"


def test_fingerprint_collapses_volatile_tokens(buffer, monkeypatch):
    # Two failures whose stderr differs only by digits/paths must share a bucket.
    stderrs = iter(["rate limit after 1234ms /tmp/goose-aaa",
                    "rate limit after 99ms /tmp/goose-bbb"])
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(returncode=1, stderr=next(stderrs)))
    goose_json.ask("p", SCHEMA, retries=1, label="t")
    goose_json.ask("p", SCHEMA, retries=1, label="t")
    recs = _records(buffer)
    nonzero = [r for r in recs if r["failure_class"] == "nonzero_exit"]
    assert len(nonzero) == 2
    assert nonzero[0]["fingerprint"] == nonzero[1]["fingerprint"]


def test_fingerprint_differs_by_failure_class(buffer):
    a = goose_json._fingerprint("timeout", "t", "")
    b = goose_json._fingerprint("nonzero_exit", "t", "")
    assert a != b


def test_stderr_excerpt_truncated_to_cap(buffer, monkeypatch):
    big = "E" * (goose_json.STDERR_EXCERPT_MAX + 500)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _proc(returncode=1, stderr=big))
    goose_json.ask("p", SCHEMA, retries=1)
    rec = _records(buffer)[0]
    assert len(rec["stderr_excerpt"]) <= goose_json.STDERR_EXCERPT_MAX + 3
    assert rec["stderr_excerpt"].startswith("...")


def test_write_failure_does_not_break_ask(monkeypatch, tmp_path):
    # An unwritable buffer must not turn a Goose failure into a crash.
    monkeypatch.setattr(goose_json, "FAILURE_DIR", tmp_path / "x")
    monkeypatch.setattr(goose_json, "_REPO_SLUG_CACHE", ["o/r"])

    def explode(*a, **k):
        raise OSError("read-only fs")
    monkeypatch.setattr(Path, "mkdir", explode)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _proc(returncode=1))
    assert goose_json.ask("p", SCHEMA, retries=1) is None  # no raise

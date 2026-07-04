"""Tests for agentic_os.tool_failures: the GlitchTip failure-record shipper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_os.tool_failures import buffer, dsn as dsn_mod, envelope, ship


def _record(**over) -> dict:
    base = {
        "ts": 1_700_000_000,
        "harness": "goose",
        "source": "goose_json.ask",
        "repo": "agentic-os",
        "failure_class": "nonzero_exit",
        "schema_title": "urgency",
        "exit_code": 1,
        "attempt": 0,
        "stderr_excerpt": "boom",
        "detail": "goose failed",
        "fingerprint": "abc123",
    }
    base.update(over)
    return base


def _write_buffer(directory: Path, slug: str, records: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slug}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return path


# --- gate ---------------------------------------------------------------


def test_is_genuine_gates_expected_and_incomplete():
    assert buffer.is_genuine(_record()) is True
    assert buffer.is_genuine(_record(expected=True)) is False
    assert buffer.is_genuine(_record(fingerprint="")) is False
    assert buffer.is_genuine({"failure_class": "x"}) is False
    assert buffer.is_genuine("not a dict") is False


# --- buffer discovery + watermark --------------------------------------


def test_buffer_files_excludes_dotfiles(tmp_path: Path):
    _write_buffer(tmp_path, "agentic-os", [_record()])
    (tmp_path / ".ship-watermarks.json").write_text("{}", encoding="utf-8")
    files = buffer.buffer_files(tmp_path)
    assert [p.name for p in files] == ["agentic-os.jsonl"]
    assert buffer.repo_slug(files[0]) == "agentic-os"


def test_watermark_roundtrip(tmp_path: Path):
    buffer.save_watermarks(tmp_path, {"agentic-os.jsonl": 42})
    assert buffer.load_watermarks(tmp_path) == {"agentic-os.jsonl": 42}


def test_load_watermarks_corrupt_is_empty(tmp_path: Path):
    buffer.watermark_path(tmp_path).write_text("{ not json", encoding="utf-8")
    assert buffer.load_watermarks(tmp_path) == {}


def test_drain_resumes_from_offset(tmp_path: Path):
    path = _write_buffer(tmp_path, "r", [_record(fingerprint="a")])
    first = list(buffer.drain_records(path, 0))
    assert len(first) == 1
    end = first[0][1]
    _write_buffer(tmp_path, "r", [_record(fingerprint="b")])
    second = list(buffer.drain_records(path, end))
    assert [r["fingerprint"] for r, _ in second] == ["b"]


def test_drain_truncation_resets(tmp_path: Path):
    path = _write_buffer(tmp_path, "r", [_record()])
    # Watermark past a now-shorter file: re-read from start.
    got = list(buffer.drain_records(path, 10_000))
    assert len(got) == 1


def test_drain_unparseable_line_yields_none(tmp_path: Path):
    path = tmp_path / "r.jsonl"
    tmp_path.mkdir(parents=True, exist_ok=True)
    path.write_text("not json\n" + json.dumps(_record()) + "\n", encoding="utf-8")
    got = list(buffer.drain_records(path, 0))
    assert got[0][0] is None
    assert got[1][0] is not None


# --- DSN ----------------------------------------------------------------


def test_parse_dsn_basic():
    parsed = dsn_mod.parse_dsn("https://pub@glitchtip.example/7")
    assert parsed.public_key == "pub"
    assert parsed.envelope_url == "https://glitchtip.example/api/7/envelope/"
    assert "sentry_key=pub" in parsed.auth_header


def test_parse_dsn_with_path_prefix_and_port():
    parsed = dsn_mod.parse_dsn("http://k@host:9000/base/12")
    assert parsed.envelope_url == "http://host:9000/base/api/12/envelope/"


@pytest.mark.parametrize("bad", ["https://host/7", "https://pub@host/", "notaurl"])
def test_parse_dsn_rejects_malformed(bad):
    with pytest.raises(ValueError):
        dsn_mod.parse_dsn(bad)


def test_resolve_dsn_env_override(monkeypatch):
    dsn_mod.clear_cache()
    monkeypatch.setenv("TOOL_FAILURES_DSN", "https://pub@host/1")
    assert dsn_mod.resolve_dsn() == "https://pub@host/1"


def test_resolve_dsn_fail_soft(monkeypatch):
    dsn_mod.clear_cache()
    monkeypatch.delenv("TOOL_FAILURES_DSN", raising=False)
    monkeypatch.setattr(dsn_mod, "_read_ssm", lambda path: None)
    assert dsn_mod.resolve_dsn(use_cache=False) is None


# --- envelope -----------------------------------------------------------


def test_build_event_fingerprint_tags_extra():
    event = envelope.build_event(
        _record(harness="claude", tool="Bash", session_id="s1")
    )
    assert event["fingerprint"] == ["abc123"]
    assert event["message"] == "claude tool failure: nonzero_exit"
    assert event["tags"]["harness"] == "claude"
    assert event["tags"]["failure_class"] == "nonzero_exit"
    assert event["tags"]["repo"] == "agentic-os"
    # Volatile detail rides in extra, never the message/title.
    assert event["extra"]["stderr_excerpt"] == "boom"
    assert event["extra"]["session_id"] == "s1"
    assert "stderr_excerpt" not in event["message"]


def test_build_envelope_is_three_lines():
    event = envelope.build_event(_record())
    body = envelope.build_envelope(event)
    lines = body.rstrip(b"\n").split(b"\n")
    assert len(lines) == 3
    header = json.loads(lines[0])
    item = json.loads(lines[1])
    assert header["event_id"] == event["event_id"]
    assert item["type"] == "event"
    assert item["length"] == len(lines[2])


# --- ship orchestration -------------------------------------------------


def test_ship_dry_run_counts_without_watermark(tmp_path: Path):
    _write_buffer(tmp_path, "r", [_record(fingerprint="a"), _record(expected=True)])
    summary = ship.ship(directory=tmp_path, dry_run=True)
    assert summary.shipped == 1
    assert summary.skipped == 1
    # Dry run leaves no watermark, so a real run still sees the records.
    assert buffer.load_watermarks(tmp_path) == {}


def test_ship_fail_soft_leaves_watermarks(tmp_path: Path, monkeypatch):
    dsn_mod.clear_cache()
    monkeypatch.delenv("TOOL_FAILURES_DSN", raising=False)
    monkeypatch.setattr(dsn_mod, "_read_ssm", lambda path: None)
    _write_buffer(tmp_path, "r", [_record()])
    summary = ship.ship(directory=tmp_path)
    assert summary.dsn_present is False
    assert summary.shipped == 0
    assert buffer.load_watermarks(tmp_path) == {}


def test_ship_happy_path_and_idempotent(tmp_path: Path, monkeypatch):
    dsn_mod.clear_cache()
    monkeypatch.setenv("TOOL_FAILURES_DSN", "https://pub@host/1")
    posted: list[str] = []
    monkeypatch.setattr(
        ship, "_post_envelope", lambda url, auth, body, *, timeout: posted.append(url)
    )
    _write_buffer(tmp_path, "r", [_record(fingerprint="a"), _record(expected=True)])

    first = ship.ship(directory=tmp_path)
    assert first.shipped == 1
    assert first.skipped == 1
    assert len(posted) == 1

    # Re-run ships nothing (watermark past everything).
    second = ship.ship(directory=tmp_path)
    assert second.shipped == 0
    assert len(posted) == 1

    # A newly appended failure ships on the next run only.
    _write_buffer(tmp_path, "r", [_record(fingerprint="c")])
    third = ship.ship(directory=tmp_path)
    assert third.shipped == 1
    assert len(posted) == 2


def test_ship_stops_and_persists_on_post_failure(tmp_path: Path, monkeypatch):
    dsn_mod.clear_cache()
    monkeypatch.setenv("TOOL_FAILURES_DSN", "https://pub@host/1")
    calls = {"n": 0}

    def flaky(url, auth, body, *, timeout):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("network down")

    monkeypatch.setattr(ship, "_post_envelope", flaky)
    _write_buffer(
        tmp_path,
        "r",
        [_record(fingerprint="a"), _record(fingerprint="b"), _record(fingerprint="c")],
    )

    summary = ship.ship(directory=tmp_path)
    assert summary.shipped == 1
    assert summary.failed == 1

    # Watermark sits after the accepted line; retry (now healthy) resumes there.
    monkeypatch.setattr(ship, "_post_envelope", lambda *a, **k: None)
    retry = ship.ship(directory=tmp_path)
    assert retry.shipped == 2  # b (previously failed) + c
    assert retry.failed == 0


def test_ship_repo_filter(tmp_path: Path, monkeypatch):
    dsn_mod.clear_cache()
    monkeypatch.setenv("TOOL_FAILURES_DSN", "https://pub@host/1")
    monkeypatch.setattr(ship, "_post_envelope", lambda *a, **k: None)
    _write_buffer(tmp_path, "one", [_record(fingerprint="a")])
    _write_buffer(tmp_path, "two", [_record(fingerprint="b")])
    summary = ship.ship(directory=tmp_path, repo="one")
    assert summary.files == 1
    assert summary.shipped == 1


def test_main_exit_code_fail_soft(tmp_path: Path, monkeypatch, capsys):
    dsn_mod.clear_cache()
    monkeypatch.delenv("TOOL_FAILURES_DSN", raising=False)
    monkeypatch.setattr(dsn_mod, "_read_ssm", lambda path: None)
    _write_buffer(tmp_path, "r", [_record()])
    code = ship.main(["--buffer-dir", str(tmp_path)])
    assert code == 0
    assert "no-dsn" in capsys.readouterr().out

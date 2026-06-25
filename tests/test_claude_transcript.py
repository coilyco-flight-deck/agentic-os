"""Tests for the Claude Code transcript drain (failure-record schema v1).

A drain run converts new `is_error` transcript records into failure-records in
the per-repo buffer, idempotently (byte-watermark respecting), covering subagent
(sidechain) transcripts and MCP tool errors, with an expected-non-zero classifier
that flags benign `grep` no-match / `... || true` failures. See agentic-os#249,
docs/claude-transcript-drain.md.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import claude_transcript as ct  # noqa: E402


# --- transcript-record builders (the on-disk JSONL shape, verified empirically) ---

def _assistant(tool_use_id, name, inp=None):
    return {"type": "assistant", "cwd": "/work", "uuid": f"a-{tool_use_id}",
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_use_id, "name": name,
                 "input": inp or {}}]}}


def _tool_result(tool_use_id, content, is_error=True, sidechain=False,
                 ts="2026-06-25T09:51:18Z", uuid="u-1"):
    return {"type": "user", "cwd": "/work", "isSidechain": sidechain,
            "sessionId": "sess-1", "uuid": uuid, "timestamp": ts,
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_use_id,
                 "is_error": is_error, "content": content}]}}


def _write(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A transcript root + isolated buffer/watermark, with the repo slug pinned
    so resolution never shells out to git in the test."""
    root = tmp_path / "projects" / "-work"
    root.mkdir(parents=True)
    failure_dir = tmp_path / "buffer"
    state = failure_dir / "wm.json"
    monkeypatch.setattr(ct, "_slug_for_cwd", lambda cwd: "owner/repo")
    return {"root": tmp_path / "projects", "failure_dir": failure_dir,
            "state": state, "sess": root / "sess-1.jsonl"}


def _records(env, repo="owner-repo") -> list[dict]:
    path = env["failure_dir"] / f"{repo}.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def _drain(env, **kw):
    return ct.drain(env["root"], failure_dir=env["failure_dir"],
                    state_file=env["state"], **kw)


# --- core extraction + mapping ---

def test_bash_nonzero_exit_extracted_with_code(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "false"}),
        _tool_result("t1", "boom\nExit code 7"),
    ])
    summary = _drain(env)
    recs = _records(env)
    assert summary["errors_found"] == 1 and summary["written"] == 1
    r = recs[0]
    assert r["harness"] == "claude" and r["source"] == "claude_transcript"
    assert r["repo"] == "owner/repo"
    assert r["failure_class"] == "nonzero_exit"
    assert r["exit_code"] == 7
    assert r["tool"] == "Bash" and r["schema_title"] == "Bash"
    assert r["expected"] is False


def test_success_results_are_ignored(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "true"}),
        _tool_result("t1", "ok", is_error=False),
    ])
    assert _drain(env)["errors_found"] == 0
    assert _records(env) == []


def test_full_schema_v1_fields_present(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "false"}),
        _tool_result("t1", "x\nExit code 1"),
    ])
    _drain(env)
    r = _records(env)[0]
    for field in ("ts", "harness", "source", "repo", "failure_class",
                  "schema_title", "tool", "exit_code", "attempt",
                  "stderr_excerpt", "detail", "expected", "fingerprint"):
        assert field in r, field
    assert isinstance(r["ts"], int) and r["ts"] > 0


def test_edit_no_match_is_client_validated_error(env):
    _write(env["sess"], [
        _assistant("t1", "Edit", {"file_path": "/work/a.py"}),
        _tool_result("t1", "<tool_use_error>String to replace not found in file.</tool_use_error>"),
    ])
    _drain(env)
    r = _records(env)[0]
    assert r["failure_class"] == "edit_no_match"
    assert r["exit_code"] is None
    assert r["expected"] is False


def test_mcp_tool_error_classified(env):
    _write(env["sess"], [
        _assistant("t1", "mcp__github__create_issue", {}),
        _tool_result("t1", "API rate limited"),
    ])
    r = _records(env)[0] if (_drain(env), _records(env))[1] else None
    assert r is not None
    assert r["failure_class"] == "mcp_error"
    assert r["tool"] == "mcp__github__create_issue"


def test_sidechain_transcript_covered(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "false"}),
        _tool_result("t1", "Exit code 2", sidechain=True),
    ])
    _drain(env)
    r = _records(env)[0]
    assert r["is_sidechain"] is True


# --- expected-non-zero classifier ---

@pytest.mark.parametrize("command,exit_code,expected", [
    ("grep foo file", 1, True),          # no match
    ("grep foo file", 2, False),         # real grep error
    ("rg pattern", 1, True),
    ("cat x | grep y", 1, True),         # pipeline tail is grep
    ("grep y | wc -l", 1, False),        # tail is wc, not expected
    ("test -f /nope", 1, True),
    ("diff a b", 1, True),
    ("somecmd || true", 3, True),        # explicitly tolerated
    ("make build", 1, False),            # genuine
])
def test_expected_classifier(command, exit_code, expected):
    assert ct._is_expected("Bash", command, exit_code) is expected


def test_non_bash_tool_is_never_expected():
    assert ct._is_expected("Read", "", None) is False


def test_summary_splits_genuine_and_expected(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "grep foo f"}),
        _tool_result("t1", "Exit code 1", uuid="u1"),
        _assistant("t2", "Bash", {"command": "make"}),
        _tool_result("t2", "Exit code 2", uuid="u2"),
    ])
    s = _drain(env)
    assert s["errors_found"] == 2
    assert s["expected"] == 1 and s["genuine"] == 1


# --- idempotency / watermark ---

def test_resweep_is_idempotent(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "false"}),
        _tool_result("t1", "Exit code 1"),
    ])
    _drain(env)
    assert len(_records(env)) == 1
    _drain(env)  # nothing new appended
    assert len(_records(env)) == 1


def test_appended_records_drained_on_next_sweep(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "false"}),
        _tool_result("t1", "Exit code 1", uuid="u1"),
    ])
    _drain(env)
    # append a second error to the same transcript
    with env["sess"].open("a") as f:
        f.write(json.dumps(_assistant("t2", "Bash", {"command": "false"})) + "\n")
        f.write(json.dumps(_tool_result("t2", "Exit code 2", uuid="u2")) + "\n")
    _drain(env)
    recs = _records(env)
    assert len(recs) == 2
    assert {r["exit_code"] for r in recs} == {1, 2}


def test_truncated_file_resets_watermark(env):
    # A long first transcript drives the watermark well past the byte length of
    # the shorter post-rotation file.
    first = []
    for i in range(8):
        first += [_assistant(f"t{i}", "Bash", {"command": "echo " + "x" * 40}),
                  _tool_result(f"t{i}", "Exit code 9", uuid=f"u{i}")]
    _write(env["sess"], first)
    _drain(env)
    # rewrite the file genuinely shorter (rotation) with a fresh error
    _write(env["sess"], [
        _assistant("t2", "Bash", {"command": "false"}),
        _tool_result("t2", "Exit code 3", uuid="new"),
    ])
    _drain(env)
    codes = [r["exit_code"] for r in _records(env)]
    assert 3 in codes  # the post-truncation error was drained, not skipped


def test_dry_run_writes_nothing_and_keeps_watermark(env):
    _write(env["sess"], [
        _assistant("t1", "Bash", {"command": "false"}),
        _tool_result("t1", "Exit code 1"),
    ])
    s = _drain(env, dry_run=True)
    assert s["errors_found"] == 1 and s["written"] == 0
    assert _records(env) == []
    assert not env["state"].exists()
    # a real sweep afterward still sees the error (watermark was not advanced)
    assert _drain(env)["written"] == 1


# --- fingerprint ---

def test_fingerprint_collapses_volatile_tokens():
    a = ct._fingerprint("nonzero_exit", "Bash", "fail at /tmp/x-123 after 5ms")
    b = ct._fingerprint("nonzero_exit", "Bash", "fail at /tmp/y-999 after 88ms")
    assert a == b


def test_fingerprint_differs_by_tool():
    a = ct._fingerprint("nonzero_exit", "Bash", "x")
    b = ct._fingerprint("nonzero_exit", "Read", "x")
    assert a != b


def test_list_content_blocks_flattened(env):
    _write(env["sess"], [
        _assistant("t1", "Read", {"file_path": "/work/missing.py"}),
        _tool_result("t1", [{"type": "text", "text": "File does not exist."}]),
    ])
    _drain(env)
    r = _records(env)[0]
    assert r["failure_class"] == "file_not_found"
    assert "File does not exist" in r["stderr_excerpt"]

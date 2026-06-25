"""Tests for goose-triage's ward-kdl forgejo I/O layer.

All forgejo reads and writes route through `ward ops forgejo` (ward-kdl), which
authenticates as the coilyco-ops bot from SSM, so the script no longer needs
FORGEJO_TOKEN (coilyco-flight-deck/agentic-os#267). These lock the command
construction and the create-if-absent comment behavior that the missing
issue-comment-edit verb forces.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("goose_triage", SCRIPTS / "goose-triage.py")
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


def _fake_run(captured, *, returncode=0, stdout="", stderr=""):
    """A subprocess.run stand-in that records argv and returns a fixed result."""
    def run(cmd, capture_output=True, text=True, timeout=60):
        captured.append(cmd)
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return run


def test_split_repo_ok():
    assert gt._split_repo("coilyco-flight-deck/ward") == ("coilyco-flight-deck", "ward")


@pytest.mark.parametrize("bad", ["ward", "", "/ward", "owner/"])
def test_split_repo_rejects_non_slug(bad):
    with pytest.raises(ValueError):
        gt._split_repo(bad)


def test_fj_appends_json_output_and_parses(monkeypatch):
    cap = []
    monkeypatch.setattr(gt.subprocess, "run", _fake_run(cap, stdout='[{"number": 1}]'))
    out = gt._fj(["issue", "list", "o", "r"])
    assert out == [{"number": 1}]
    assert cap[0] == [gt.WARD, "ops", "forgejo", "issue", "list", "o", "r", "--output", "json"]


def test_fj_write_call_omits_json_and_returns_none(monkeypatch):
    cap = []
    monkeypatch.setattr(gt.subprocess, "run", _fake_run(cap, stdout="ok"))
    assert gt._fj(["issue-label", "add", "o", "r", "5", "--labels", "P1"], parse=False) is None
    assert "--output" not in cap[0]


def test_fj_nonzero_raises_with_stderr(monkeypatch):
    monkeypatch.setattr(gt.subprocess, "run",
                        _fake_run([], returncode=1, stderr="denied by policy"))
    with pytest.raises(gt.WardForgejoError, match="denied by policy"):
        gt._fj(["issue", "list", "o", "r"])


def test_fetch_issues_builds_list_all_call_and_drops_prs(monkeypatch):
    cap = []
    payload = ('[{"number": 1, "title": "a", "body": "b"},'
               ' {"number": 2, "title": "pr", "body": "", "pull_request": {"url": "x"}}]')
    monkeypatch.setattr(gt.subprocess, "run", _fake_run(cap, stdout=payload))
    issues = gt.fetch_issues("coilyco-flight-deck/ward")
    assert [it["num"] for it in issues] == [1]  # the PR is filtered out
    # list-all auto-paginates the whole backlog: no --limit cap (agentic-os#270).
    assert cap[0] == [gt.WARD, "ops", "forgejo", "issue", "list-all",
                      "coilyco-flight-deck", "ward",
                      "--state", "open", "--type", "issues",
                      "--output", "json"]


def test_label_add_passes_each_label_flag(monkeypatch):
    cap = []
    monkeypatch.setattr(gt.subprocess, "run", _fake_run(cap))
    rc, err = gt._label("o/r", 7, "add", ["P1"])
    assert (rc, err) == (0, "")
    assert cap[0] == [gt.WARD, "ops", "forgejo", "issue-label", "add",
                      "o", "r", "7", "--labels", "P1"]


def test_label_remove_deletes_each_by_name(monkeypatch):
    cap = []
    monkeypatch.setattr(gt.subprocess, "run", _fake_run(cap))
    gt._label("o/r", 7, "remove", ["P2", "P3"])
    assert [c[-1] for c in cap] == ["P2", "P3"]  # one remove per label, by name
    assert all(c[3:6] == ["issue-label", "remove", "o"] for c in cap)


def test_label_unknown_verb_is_reported():
    rc, err = gt._label("o/r", 1, "frobnicate", ["P1"])
    assert rc == 1 and "frobnicate" in err


def test_label_failure_is_caught(monkeypatch):
    monkeypatch.setattr(gt.subprocess, "run",
                        _fake_run([], returncode=1, stderr="boom"))
    rc, err = gt._label("o/r", 1, "add", ["P1"])
    assert rc == 1 and "boom" in err


def test_upsert_comment_creates_when_absent(monkeypatch):
    cap = []

    def fake_fj(args, parse=True, timeout=60):
        cap.append(args)
        if args[:2] == ["issue-comment", "list"]:
            return []  # no prior comment
        return None

    monkeypatch.setattr(gt, "_fj", fake_fj)
    it = {"num": 3, "title": "t", "tier": "P2", "mode": "headless"}
    assert gt.upsert_comment("o/r", it, "2026-06-23") == "created"
    assert cap[-1][:3] == ["issue", "comment", "o"]


def test_upsert_comment_skips_when_marker_present(monkeypatch):
    def fake_fj(args, parse=True, timeout=60):
        if args[:2] == ["issue-comment", "list"]:
            return [{"id": 9, "body": gt.COMMENT_MARKER + "\nold verdict"}]
        raise AssertionError("must not write when a marked comment already exists")

    monkeypatch.setattr(gt, "_fj", fake_fj)
    it = {"num": 3, "title": "t", "tier": "P2", "mode": "headless"}
    assert gt.upsert_comment("o/r", it, "2026-06-23") == "skipped"


def test_upsert_comment_failure_is_reported(monkeypatch):
    def fake_fj(args, parse=True, timeout=60):
        raise gt.WardForgejoError("list failed")

    monkeypatch.setattr(gt, "_fj", fake_fj)
    it = {"num": 3, "title": "t", "tier": "P2", "mode": "headless"}
    out = gt.upsert_comment("o/r", it, "2026-06-23")
    assert out.startswith("FAILED") and "list failed" in out

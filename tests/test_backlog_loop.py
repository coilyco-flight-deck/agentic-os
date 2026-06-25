"""Tests for backlog-loop: the supervised ralph-loop backbone.

Cover the deterministic core - lane assignment + ranking, the durable ledger
round-trip, WARD-OUTCOME parsing, and the docker-poll classification - with all
ward/forgejo/docker subprocess calls stubbed. No live ward, no containers.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("backlog_loop", SCRIPTS / "backlog-loop.py")
bl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bl)


def _issue(num, title="t", labels=None, url=""):
    return {"number": num, "title": title, "labels": labels or [], "html_url": url}


# --- lane + tier classification -------------------------------------------

def test_tier_and_mode_extraction():
    assert bl._tier_of(["interactive", "P2"]) == "P2"
    assert bl._mode_of(["interactive", "P2"]) == "interactive"
    assert bl._tier_of(["no-tier"]) is None
    assert bl._mode_of(["P1"]) is None


def test_tier_picks_highest_when_multiple():
    assert bl._tier_of(["P3", "P0"]) == "P0"


def test_label_names_handles_objects_and_strings():
    # `issue list` returns label objects; the lean projection returns strings.
    assert bl._label_names([{"name": "P2", "color": "x"}, {"name": "headless"}]) == ["P2", "headless"]
    assert bl._label_names(["P1", "consult"]) == ["P1", "consult"]
    assert bl._label_names([]) == []
    assert bl._label_names([{"color": "x"}]) == []


@pytest.mark.parametrize("tier,mode,lane", [
    ("P1", "headless", "headless"),
    ("P2", "interactive", "interactive"),
    ("P3", "consult", "consult"),
    (None, "headless", "untriaged"),
    ("P1", None, "untriaged"),
    (None, None, "untriaged"),
])
def test_lane_for(tier, mode, lane):
    assert bl._lane_for(tier, mode) == lane


# --- ranking ---------------------------------------------------------------

def test_rank_orders_headless_before_interactive_then_tier():
    issues = [
        _issue(10, labels=["interactive", "P0"]),
        _issue(11, labels=["headless", "P3"]),
        _issue(12, labels=["headless", "P1"]),
    ]
    ranked = bl.rank(issues, scores={})
    # headless lane first regardless of tier, then by tier within lane.
    assert [r["num"] for r in ranked] == [12, 11, 10]
    assert [r["lane"] for r in ranked] == ["headless", "headless", "interactive"]


def test_rank_breaks_tier_ties_by_score_then_number():
    issues = [
        _issue(20, labels=["headless", "P2"]),
        _issue(21, labels=["headless", "P2"]),
    ]
    ranked = bl.rank(issues, scores={21: 90.0, 20: 50.0})
    assert [r["num"] for r in ranked] == [21, 20]


# --- ledger round-trip -----------------------------------------------------

def test_ledger_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(bl, "CACHE_DIR", tmp_path)
    led = {"repo": "o/r", "issues": {"5": {"num": 5, "state": "queued", "lane": "headless"}}}
    path = bl.save_ledger(led)
    assert path.exists()
    back = bl.load_ledger("o/r")
    assert back["issues"]["5"]["state"] == "queued"
    assert back["updated"] is not None


def test_load_ledger_fresh_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(bl, "CACHE_DIR", tmp_path)
    led = bl.load_ledger("o/missing")
    assert led["issues"] == {}
    assert led["repo"] == "o/missing"


# --- select: re-queue on lane promotion ------------------------------------

def _select_with(monkeypatch, tmp_path, issues, prior_ledger=None):
    """Run cmd_select with the backlog + triage stubbed and an optional prior ledger."""
    monkeypatch.setattr(bl, "CACHE_DIR", tmp_path)
    if prior_ledger is not None:
        bl.save_ledger(prior_ledger)
    monkeypatch.setattr(bl, "fetch_open_issues", lambda repo, limit: issues)
    monkeypatch.setattr(bl, "_latest_triage_scores", lambda repo: {})
    bl.cmd_select("o/r", 50)
    return bl.load_ledger("o/r")


def test_select_requeues_issue_newly_promoted_to_headless(tmp_path, monkeypatch):
    # #79 was a consult-lane issue parked at `skipped`; a re-triage relabelled it
    # headless. Select must reset it to queued so `next --lane headless` sees it.
    prior = {"repo": "o/r", "issues": {
        "79": {"num": 79, "state": "skipped", "lane": "consult", "unblock_history": []},
    }}
    after = _select_with(monkeypatch, tmp_path,
                         [_issue(79, labels=["headless", "P1"])], prior)
    assert after["issues"]["79"]["lane"] == "headless"
    assert after["issues"]["79"]["state"] == "queued"
    # And `next --lane headless` now surfaces it.
    picks = [e["num"] for e in bl._by_lane(after).get("headless", []) if e["state"] == "queued"]
    assert 79 in picks


def test_select_requeues_surfaced_interactive_promoted_to_headless(tmp_path, monkeypatch):
    prior = {"repo": "o/r", "issues": {
        "80": {"num": 80, "state": "surfaced", "lane": "interactive", "unblock_history": []},
    }}
    after = _select_with(monkeypatch, tmp_path,
                         [_issue(80, labels=["headless", "P2"])], prior)
    assert after["issues"]["80"]["state"] == "queued"


@pytest.mark.parametrize("state", ["dispatched", "blocked", "done", "failed"])
def test_select_preserves_in_flight_state_on_promotion(tmp_path, monkeypatch, state):
    # A live/terminal state must survive a re-select - never clobber a running
    # container or finished work just because the lane was recomputed.
    prior = {"repo": "o/r", "issues": {
        "81": {"num": 81, "state": state, "lane": "headless", "unblock_history": []},
    }}
    after = _select_with(monkeypatch, tmp_path,
                         [_issue(81, labels=["headless", "P1"])], prior)
    assert after["issues"]["81"]["state"] == state


def test_select_leaves_consult_issue_skipped(tmp_path, monkeypatch):
    # An issue that stays in consult is not promoted, so it keeps `skipped`.
    prior = {"repo": "o/r", "issues": {
        "82": {"num": 82, "state": "skipped", "lane": "consult", "unblock_history": []},
    }}
    after = _select_with(monkeypatch, tmp_path,
                         [_issue(82, labels=["consult", "P3"])], prior)
    assert after["issues"]["82"]["state"] == "skipped"


# --- WARD-OUTCOME parsing --------------------------------------------------

def test_parse_outcome_none_when_no_marker():
    assert bl.parse_outcome([{"body": "just a normal comment", "created_at": "1"}]) is None


def test_parse_outcome_done():
    # The reason/retro lives below the marker line; the outcome text is same-line.
    out = bl.parse_outcome([{"body": "WARD-OUTCOME: done\nfelt smooth", "created_at": "1"}])
    assert out == {"status": "done", "text": ""}


def test_parse_outcome_ignores_dispatch_protocol_comment():
    # The protocol comment embeds the marker as examples; never read it as an outcome.
    assert bl.parse_outcome([{"body": bl.DISPATCH_PROTOCOL, "created_at": "1"}]) is None


def test_parse_outcome_marker_must_lead_a_line():
    # A marker buried mid-prose (e.g. quoted in a discussion) is not an outcome.
    body = "I think the agent should post `WARD-OUTCOME: done` when finished."
    assert bl.parse_outcome([{"body": body, "created_at": "1"}]) is None


def test_parse_outcome_blocked_captures_question():
    body = "WARD-OUTCOME: blocked - need the prod DSN to wire Sentry\n\nretro: stuck early"
    out = bl.parse_outcome([{"body": body, "created_at": "1"}])
    assert out["status"] == "blocked"
    assert "prod DSN" in out["text"]
    # The blank-line retro tail is not folded into the blocker text.
    assert "retro" not in out["text"]


def test_parse_outcome_takes_latest_by_created_at():
    comments = [
        {"body": "WARD-OUTCOME: blocked - first", "created_at": "2026-01-01T00:00:00Z"},
        {"body": "WARD-OUTCOME: done - resolved", "created_at": "2026-01-02T00:00:00Z"},
    ]
    assert bl.parse_outcome(comments)["status"] == "done"


def test_parse_outcome_unknown_status():
    out = bl.parse_outcome([{"body": "WARD-OUTCOME: maybe?", "created_at": "1"}])
    assert out["status"] == "unknown"


# --- poll classification ---------------------------------------------------

def test_poll_classifies_exited_container_by_outcome(tmp_path, monkeypatch):
    monkeypatch.setattr(bl, "CACHE_DIR", tmp_path)
    led = {"repo": "o/r", "issues": {
        "7": {"num": 7, "state": "dispatched", "lane": "headless"},
        "8": {"num": 8, "state": "dispatched", "lane": "headless"},
    }}
    bl.save_ledger(led)
    # #7's container is gone and it posted blocked; #8 is still running.
    monkeypatch.setattr(bl, "_container_for_issue",
                        lambda num, repo: None if num == 7 else "ward-r-issue-8-claude-x")
    monkeypatch.setattr(bl, "read_outcome",
                        lambda repo, num: {"status": "blocked", "text": "need a decision"})
    bl.cmd_poll("o/r")
    after = bl.load_ledger("o/r")
    assert after["issues"]["7"]["state"] == "blocked"
    assert after["issues"]["8"]["state"] == "dispatched"


def test_poll_flags_exit_with_no_outcome(tmp_path, monkeypatch):
    monkeypatch.setattr(bl, "CACHE_DIR", tmp_path)
    led = {"repo": "o/r", "issues": {"9": {"num": 9, "state": "dispatched", "lane": "headless"}}}
    bl.save_ledger(led)
    monkeypatch.setattr(bl, "_container_for_issue", lambda num, repo: None)
    monkeypatch.setattr(bl, "read_outcome", lambda repo, num: None)
    bl.cmd_poll("o/r")
    after = bl.load_ledger("o/r")
    assert after["issues"]["9"]["state"] == "dispatched"
    assert after["issues"]["9"]["last_outcome"]["status"] == "exited-no-outcome"


# --- forgejo command construction ------------------------------------------

def _fake_run(captured, *, returncode=0, stdout="", stderr=""):
    def run(cmd, capture_output=True, text=True, timeout=60):
        captured.append(cmd)
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return run


def test_fj_appends_json_and_parses(monkeypatch):
    cap = []
    monkeypatch.setattr(bl.subprocess, "run", _fake_run(cap, stdout='[{"number": 1}]'))
    assert bl._fj(["issue", "list", "o", "r"]) == [{"number": 1}]
    assert cap[0][-2:] == ["--output", "json"]


def test_fj_nonzero_raises(monkeypatch):
    monkeypatch.setattr(bl.subprocess, "run", _fake_run([], returncode=1, stderr="nope"))
    with pytest.raises(bl.WardError, match="nope"):
        bl._fj(["issue", "list", "o", "r"])


def test_split_repo_rejects_non_slug():
    with pytest.raises(ValueError):
        bl._split_repo("ward")

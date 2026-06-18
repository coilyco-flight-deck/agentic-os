"""Tests for goose-triage's per-pass Goose-call failure counting.

A failed model call must stop laundering into a wrong-but-valid label: runoff and
classify_mode keep their fail-soft defaults but now report when the underlying
Goose call returned None, so run() can count it. See docs/goose-triage.md, #248.
"""
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("goose_triage", SCRIPTS / "goose-triage.py")
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


def test_runoff_reports_call_failure(monkeypatch):
    monkeypatch.setattr(gt, "ask", lambda *a, **k: None)
    members = [{"num": 1, "title": "a"}, {"num": 2, "title": "b"}]
    ok, failed = gt.runoff(members, "o/r")
    assert ok is False and failed is True


def test_runoff_success_is_not_a_failure(monkeypatch):
    monkeypatch.setattr(gt, "ask", lambda *a, **k: {"order": [2, 1]})
    members = [{"num": 1, "title": "a"}, {"num": 2, "title": "b"}]
    ok, failed = gt.runoff(members, "o/r")
    assert ok is True and failed is False
    assert members[1]["tiebreak"] == 0  # #2 ranked first


def test_runoff_usable_but_empty_order_is_not_a_call_failure(monkeypatch):
    # A valid response with an unusable order is not a Goose-call failure.
    monkeypatch.setattr(gt, "ask", lambda *a, **k: {"order": []})
    ok, failed = gt.runoff([{"num": 1, "title": "a"}], "o/r")
    assert ok is False and failed is False


def test_classify_mode_reports_call_failure_and_defaults(monkeypatch):
    monkeypatch.setattr(gt, "ask", lambda *a, **k: None)
    mode, reason, failed = gt.classify_mode({"num": 1, "title": "t", "body": ""}, "o/r")
    assert mode == gt.MODE_DEFAULT and failed is True


def test_classify_mode_high_confidence_is_not_a_failure(monkeypatch):
    monkeypatch.setattr(gt, "ask", lambda *a, **k: {
        "mode": "headless", "confidence": "high", "reason": "clear"})
    mode, reason, failed = gt.classify_mode({"num": 1, "title": "t", "body": ""}, "o/r")
    assert mode == "headless" and failed is False

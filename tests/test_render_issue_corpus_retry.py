"""Retry behavior for render-issue-corpus's `_fj` ward shell-out (agentic-os#280).

A transient `ward` not-found mid-run (a brew symlink-swap window, PATH churn) used
to drop the shell-out with no retry, stranding whatever the call was reading or
writing. `_fj` now rides out that momentary window with bounded exponential backoff
and only fails once a persistent absence exhausts the attempts. These tests pin that
contract: recovery on a transient miss, loud failure on a persistent one, and no
retry on an ordinary non-zero exit (a real API error must surface immediately).

The whole render-issue-corpus test suite was removed with the exec'd-command era
(03d1525); this file re-adds only the coverage the #280 fix needs, not that suite.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("render_issue_corpus",
                                               SCRIPTS / "render-issue-corpus.py")
ric = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ric)


def _capture_sleeps(monkeypatch):
    """Swap the backoff sleep for a recorder so the tests never actually wait."""
    slept: list[float] = []
    monkeypatch.setattr(ric, "_sleep", slept.append)
    return slept


def test_fj_retries_transient_not_found_then_succeeds(monkeypatch):
    """A `ward` not-found on the first attempts, resolving before the cap, recovers
    the call - the exact brew symlink-swap window agentic-os#280 documents."""
    slept = _capture_sleeps(monkeypatch)
    calls = {"n": 0}

    def run(cmd, capture_output=True, text=True, timeout=120):
        calls["n"] += 1
        if calls["n"] < 3:
            raise FileNotFoundError(2, "No such file or directory: 'ward'")
        return types.SimpleNamespace(returncode=0, stdout='[{"number": 1}]', stderr="")

    monkeypatch.setattr(ric.subprocess, "run", run)
    assert ric._fj(["issue", "list-all", "o", "r"]) == [{"number": 1}]
    assert calls["n"] == 3
    # Two failed attempts -> two backoff sleeps, exponential from the base.
    assert slept == [ric._FJ_BACKOFF_BASE, ric._FJ_BACKOFF_BASE * 2]


def test_fj_persistent_not_found_reraises_after_bounded_attempts(monkeypatch):
    """A genuinely-missing ward exhausts the retries and re-raises the OSError, so
    the run fails loudly instead of the retry masking it as an empty render."""
    slept = _capture_sleeps(monkeypatch)
    calls = {"n": 0}

    def run(cmd, capture_output=True, text=True, timeout=120):
        calls["n"] += 1
        raise FileNotFoundError(2, "No such file or directory: 'ward'")

    monkeypatch.setattr(ric.subprocess, "run", run)
    with pytest.raises(OSError):
        ric._fj(["issue", "list-all", "o", "r"])
    assert calls["n"] == ric._FJ_MAX_ATTEMPTS
    assert len(slept) == ric._FJ_MAX_ATTEMPTS - 1


def test_fj_nonzero_exit_does_not_retry(monkeypatch):
    """A non-zero exit means ward ran and the API call failed - a real error that
    must surface at once, never retried like a transient not-found."""
    slept = _capture_sleeps(monkeypatch)
    calls = {"n": 0}

    def run(cmd, capture_output=True, text=True, timeout=120):
        calls["n"] += 1
        return types.SimpleNamespace(returncode=1, stdout="", stderr="denied by policy")

    monkeypatch.setattr(ric.subprocess, "run", run)
    with pytest.raises(ric.WardForgejoError, match="denied by policy"):
        ric._fj(["issue", "list-all", "o", "r"])
    assert calls["n"] == 1
    assert slept == []

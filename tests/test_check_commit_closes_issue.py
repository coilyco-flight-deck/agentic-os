"""Tests for agentic_os.check_commit_closes_issue: Forgejo-URL-only enforcement."""
from __future__ import annotations

import pytest

from agentic_os import check_commit_closes_issue as mod
from agentic_os.check_commit_closes_issue import classify, this_repo

THIS = ("coilysiren", "backend")
URL = "https://forgejo.coilysiren.me/coilysiren/backend/issues/27"


def test_same_repo_url_accepted() -> None:
    assert classify(f"fix: thing\n\ncloses {URL}", THIS) == "ok"


def test_url_without_keyword_accepted() -> None:
    # A bare URL reference (no closing keyword) is enough - the rule requires
    # a reference, not a close.
    assert classify(f"fix: thing\n\n{URL}", THIS) == "ok"


def test_inline_url_reference_accepted() -> None:
    assert classify(f"fix: thing (see {URL})", THIS) == "ok"


@pytest.mark.parametrize("kw", ["closes", "close", "closed", "fixes", "fix", "resolves", "resolved"])
def test_all_keywords_accepted(kw: str) -> None:
    assert classify(f"feat: x\n\n{kw} {URL}", THIS) == "ok"


def test_bare_hash_rejected() -> None:
    assert classify("fix: thing\n\ncloses #27", THIS) == "short-form"


def test_short_owner_repo_rejected() -> None:
    assert classify("fix: thing\n\ncloses coilysiren/backend#27", THIS) == "short-form"


def test_wrong_repo_url_rejected() -> None:
    other = "https://forgejo.coilysiren.me/coilysiren/other-repo/issues/9"
    assert classify(f"fix: thing\n\ncloses {other}", THIS) == "wrong-repo"


def test_org_split_owner_mismatch_accepted() -> None:
    # GitHub origin owner (coilyco-flight-deck) differs from the Forgejo
    # tracker owner (coilysiren); repo name still matches -> accepted.
    split = ("coilyco-flight-deck", "backend")
    assert classify(f"fix\n\ncloses {URL}", split) == "ok"


def test_no_reference() -> None:
    assert classify("chore: tidy up, no issue here", THIS) == "none"


def test_url_wins_even_with_bare_present() -> None:
    # A correct URL ref makes the commit pass regardless of other noise.
    assert classify(f"fix\n\ncloses {URL}\nsee also #5", THIS) == "ok"


def test_unknown_origin_accepts_any_forgejo_url() -> None:
    # No origin resolved: cannot enforce same-repo, accept well-formed URL.
    assert classify(f"fix\n\ncloses {URL}", None) == "ok"


def test_http_scheme_accepted() -> None:
    http = "http://forgejo.coilysiren.me/coilysiren/backend/issues/27"
    assert classify(f"fix\n\ncloses {http}", THIS) == "ok"


def test_this_repo_prefers_forgejo_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    # forgejo names the canonical owner/repo; origin is the GitHub mirror.
    remotes = {
        "forgejo": "https://forgejo.coilysiren.me/coilysiren/backend.git",
        "origin": "git@github.com:coilyco-flight-deck/backend.git",
    }
    monkeypatch.setattr(mod, "_remote_url", lambda name: remotes.get(name))
    assert this_repo() == ("coilysiren", "backend")


def test_this_repo_falls_back_to_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    # No forgejo remote configured: fall back to origin.
    remotes = {"origin": "git@github.com:coilysiren/backend.git"}
    monkeypatch.setattr(mod, "_remote_url", lambda name: remotes.get(name))
    assert this_repo() == ("coilysiren", "backend")


def test_this_repo_none_when_no_remotes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_remote_url", lambda name: None)
    assert this_repo() is None

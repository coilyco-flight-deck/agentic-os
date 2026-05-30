"""Tests for agentic_os.check_commit_closes_issue: Forgejo-URL-only enforcement."""
from __future__ import annotations

import pytest

from agentic_os.check_commit_closes_issue import classify

THIS = ("coilysiren", "backend")
URL = "https://forgejo.coilysiren.me/coilysiren/backend/issues/27"


def test_same_repo_url_accepted() -> None:
    assert classify(f"fix: thing\n\ncloses {URL}", THIS) == "ok"


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

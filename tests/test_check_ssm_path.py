"""Tests for agentic_os.pre_commit.check_ssm_path: the /<org>/<repo>/<tier>/<tail> schema."""
from __future__ import annotations

import pytest

from agentic_os.pre_commit.check_ssm_path import main, validate_path


@pytest.mark.parametrize(
    "path",
    [
        "/coilysiren/backend/write/ts-authkey",
        "/coilysiren/infrastructure/admin/tailscale-oauth-client-id",
        "/coilysiren/eco-mcp-app/read/fred-api-key",
        "/coilysiren/agentic-os/write/x",
    ],
)
def test_valid_paths(path: str) -> None:
    assert validate_path(path) == []


def test_missing_leading_slash() -> None:
    problems = validate_path("coilysiren/backend/write/x")
    assert problems and "start with '/'" in problems[0]


@pytest.mark.parametrize(
    "path",
    [
        "/coilysiren/backend/write",
        "/coilysiren/backend/write/a/b",
        "/coilysiren/backend/write/",
    ],
)
def test_too_few_or_many_segments(path: str) -> None:
    assert validate_path(path), f"expected {path!r} to be rejected"


def test_unknown_org() -> None:
    problems = validate_path("/acme/backend/write/x")
    assert any("org" in p for p in problems)


def test_bad_tier() -> None:
    problems = validate_path("/coilysiren/backend/superuser/x")
    assert any("tier" in p for p in problems)


def test_uppercase_repo_rejected() -> None:
    problems = validate_path("/coilysiren/Backend/write/x")
    assert any("repo" in p for p in problems)


@pytest.mark.parametrize("tail", ["UPPER", "under_score", "has.dot", "has/slash", ""])
def test_bad_tail(tail: str) -> None:
    problems = validate_path(f"/coilysiren/backend/write/{tail}")
    assert problems, f"expected tail {tail!r} to be rejected"


def test_collects_multiple_problems() -> None:
    problems = validate_path("/acme/Backend/superuser/Bad")
    assert len(problems) >= 3


def test_main_exit_codes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["/coilysiren/backend/write/ts-authkey"]) == 0
    assert main(["/coilysiren/backend/superuser/x"]) == 1
    assert main([]) == 2

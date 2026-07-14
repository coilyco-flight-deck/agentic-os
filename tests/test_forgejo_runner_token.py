from __future__ import annotations

from agentic_os import forgejo_runner_token


def test_parse_scope_routes_each_registration_token_shape() -> None:
    assert forgejo_runner_token.parse_scope(["global"]) == forgejo_runner_token.Scope(
        "generate-runner-token-global",
        (),
    )
    assert forgejo_runner_token.parse_scope(["org", "coilyco"]) == forgejo_runner_token.Scope(
        "generate-runner-token-org",
        ("coilyco",),
    )
    assert forgejo_runner_token.parse_scope(["repo", "coilyco", "agentic-os"]) == forgejo_runner_token.Scope(
        "generate-runner-token-repo",
        ("coilyco", "agentic-os"),
    )


def test_parse_scope_rejects_unknown_or_mis_shaped_input() -> None:
    for argv in ([], ["global", "extra"], ["org"], ["repo", "one"], ["bogus"]):
        try:
            forgejo_runner_token.parse_scope(argv)
        except ValueError as exc:
            assert "usage: generate-runner-token" in str(exc)
        else:
            raise AssertionError(f"expected ValueError for {argv!r}")

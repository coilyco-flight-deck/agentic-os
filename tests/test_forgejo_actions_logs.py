from __future__ import annotations

import pytest

from agentic_os import forgejo_actions_logs as logs


JOB_PAGE_HTML = """
<div id="repo-action-view"
	data-run-index="886"
	data-run-id="6281"
	data-job-index="0"
	data-attempt-number="1"
	data-initial-post-response="{&#34;state&#34;:{&#34;run&#34;:{&#34;jobs&#34;:[{&#34;id&#34;:10441,&#34;name&#34;:&#34;gate&#34;}]}}}"
	data-initial-artifacts-response="{&#34;artifacts&#34;:[]}"
>
</div>
"""


def test_resolve_target_maps_visible_indices_to_internal_ids(monkeypatch):
    calls: list[tuple[str, str, str]] = []

    def fake_get(url: str, token: str, accept: str) -> bytes:
        calls.append((url, token, accept))
        if accept == "text/html":
            return JOB_PAGE_HTML.encode("utf-8")
        assert accept == "text/plain"
        assert (
            url
            == "https://forgejo.example/api/v1/repos/coilyco-flight-deck/agentic-os/"
            "actions/runs/6281/jobs/10441/attempt/1/logs"
        )
        return b"line one\nline two\n"

    monkeypatch.setattr(logs, "_http_get", fake_get)
    target = logs.resolve_target(
        "coilyco-flight-deck",
        "agentic-os",
        886,
        0,
        1,
        token="secret",
        base_url="https://forgejo.example",
    )

    assert target.run_id == 6281
    assert target.job_id == 10441
    assert target.page_url("https://forgejo.example") == (
        "https://forgejo.example/coilyco-flight-deck/agentic-os/actions/runs/"
        "886/jobs/0/attempt/1"
    )
    assert calls[0] == (
        "https://forgejo.example/coilyco-flight-deck/agentic-os/actions/runs/886/"
        "jobs/0/attempt/1",
        "secret",
        "text/html",
    )


def test_fetch_logs_uses_resolved_ids(monkeypatch):
    seen: list[tuple[str, str, str]] = []

    def fake_get(url: str, token: str, accept: str) -> bytes:
        seen.append((url, token, accept))
        return b"line one\nline two\n"

    monkeypatch.setattr(logs, "_http_get", fake_get)
    target = logs.JobLogTarget(
        owner="coilyco-flight-deck",
        repo="agentic-os",
        run_index=886,
        job_index=0,
        attempt=1,
        run_id=6281,
        job_id=10441,
    )

    body = logs.fetch_logs(target, token="secret", base_url="https://forgejo.example")
    assert body == b"line one\nline two\n"
    assert seen == [
        (
            "https://forgejo.example/api/v1/repos/coilyco-flight-deck/agentic-os/"
            "actions/runs/6281/jobs/10441/attempt/1/logs",
            "secret",
            "text/plain",
        )
    ]


def test_parse_job_page_reports_missing_mapping():
    target = logs.JobLogTarget(
        owner="coilyco-flight-deck",
        repo="agentic-os",
        run_index=886,
        job_index=0,
        attempt=1,
        run_id=886,
        job_id=0,
    )

    with pytest.raises(logs.ForgejoActionsLogError, match="could not resolve Forgejo job ids"):
        logs._parse_job_page(target, "<div></div>", base_url="https://forgejo.example")

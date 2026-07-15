from __future__ import annotations

import json

import pytest

from agentic_os import forgejo_actions_logs as logs


JOB_PAGE_HTML = """
<div id="repo-action-view"
	data-run-index="886"
	data-run-id="6281"
	data-job-index="0"
	data-attempt-number="1"
	data-initial-post-response="{&#34;state&#34;:{&#34;currentJob&#34;:{&#34;steps&#34;:[{&#34;summary&#34;:&#34;Set up job&#34;,&#34;status&#34;:&#34;success&#34;},{&#34;summary&#34;:&#34;go test&#34;,&#34;status&#34;:&#34;failure&#34;}]}}}"
	data-initial-artifacts-response="{&#34;artifacts&#34;:[]}"
>
</div>
"""

CURSOR_RESPONSE = {
    "logs": {
        "stepsLog": [
            {"step": 0, "lines": [{"message": "prep line"}]},
            {"step": 1, "lines": [{"message": "--- FAIL: TestX"}, {"message": "FAIL"}]},
        ]
    }
}


def test_fetch_job_logs_uses_the_ui_log_cursor_route(monkeypatch):
    calls: list[tuple[str, str, bytes | None]] = []

    def fake_request(url, token, *, data=None, content_type=None):
        calls.append((url, token, data))
        if data is None:
            return JOB_PAGE_HTML.encode("utf-8")
        return json.dumps(CURSOR_RESPONSE).encode("utf-8")

    monkeypatch.setattr(logs, "request", fake_request)
    target = logs.JobLogTarget(
        owner="coilyco-flight-deck", repo="agentic-os", run_index=886, job_index=0, attempt=1
    )

    rendered = logs.fetch_job_logs(target, token="secret", base_url="https://forgejo.example")

    # Both calls hit the SAME attempt-qualified page URL: GET for the payload,
    # POST for the cursors. The /attempt/1 segment is load-bearing (aos#476).
    page = "https://forgejo.example/coilyco-flight-deck/agentic-os/actions/runs/886/jobs/0/attempt/1"
    assert [c[0] for c in calls] == [page, page]
    assert calls[1][2] is not None
    cursors = json.loads(calls[1][2])["logCursors"]
    assert cursors == [
        {"step": 0, "cursor": None, "expanded": True},
        {"step": 1, "cursor": None, "expanded": True},
    ]
    assert "### step 1: go test [failure]" in rendered
    assert "--- FAIL: TestX" in rendered


def test_parse_job_steps_reports_a_payloadless_page():
    with pytest.raises(logs.ForgejoActionsLogError, match="initial job payload"):
        logs.parse_job_steps("<div></div>", page_url="https://forgejo.example/x")


def test_parse_job_steps_reports_a_steps_free_job():
    page = JOB_PAGE_HTML.replace(
        "{&#34;summary&#34;:&#34;Set up job&#34;,&#34;status&#34;:&#34;success&#34;},{&#34;summary&#34;:&#34;go test&#34;,&#34;status&#34;:&#34;failure&#34;}",
        "",
    )
    with pytest.raises(logs.ForgejoActionsLogError, match="no steps"):
        logs.parse_job_steps(page, page_url="https://forgejo.example/x")


def test_attempt_defaults_to_one_in_the_cli():
    args = logs._parse_args(["o", "r", "886", "0"])
    assert args.attempt == 1

from __future__ import annotations

import json

from agentic_os import forgejo_actions_rerun as rerun


RUN_PAGE_HTML = """
<div id="repo-action-view"
\tdata-run-index="1243"
\tdata-run-id="7917"
\tdata-job-index="0"
\tdata-attempt-number="1"
\tdata-actions-url="/coilyco-flight-deck/agentic-os/actions"
\tdata-workflow-name="release.yml"
\tdata-workflow-url="/coilyco-flight-deck/agentic-os/actions?workflow=release.yml"
\tdata-workflow-source-url="/coilyco-flight-deck/agentic-os/src/commit/c2b03f9ea91c7378f0826390e63868837656fe7e/.forgejo/workflows/release.yml"
\tdata-initial-post-response="{&#34;state&#34;:{&#34;run&#34;:{&#34;link&#34;:&#34;/coilyco-flight-deck/agentic-os/actions/runs/1243&#34;,&#34;canRerun&#34;:false,&#34;jobs&#34;:[{&#34;status&#34;:&#34;success&#34;,&#34;canRerun&#34;:false},{&#34;status&#34;:&#34;failure&#34;,&#34;canRerun&#34;:true},{&#34;status&#34;:&#34;failure&#34;,&#34;canRerun&#34;:true}]}}}"
\tdata-initial-artifacts-response="{&#34;artifacts&#34;:[]}"
>
</div>
"""

RUN_METADATA = {
    "workflow_id": "release.yml",
    "event_payload": json.dumps(
        {
            "pull_request": {
                "head": {
                    "ref": "issue-473",
                }
            }
        }
    ),
}


def test_rerun_dispatches_the_workflow_when_the_web_rerun_is_unavailable(monkeypatch):
    calls: list[tuple[str, str, bytes | None]] = []

    def fake_request(url, token, *, data=None, content_type=None, auth_scheme="basic"):
        calls.append((url, token, data))
        if data is None:
            if url.endswith("/api/v1/repos/coilyco-flight-deck/agentic-os/actions/runs/7917"):
                return json.dumps(RUN_METADATA).encode("utf-8")
            return RUN_PAGE_HTML.encode("utf-8")
        return b""

    monkeypatch.setattr(rerun, "request", fake_request)

    rc = rerun.main(["rerun", "coilyco-flight-deck", "agentic-os", "1243"])

    assert rc == 0
    assert [url for url, _token, _data in calls] == [
        "https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/actions/runs/1243",
        "https://forgejo.coilysiren.me/api/v1/repos/coilyco-flight-deck/agentic-os/actions/runs/7917",
        "https://forgejo.coilysiren.me/api/v1/repos/coilyco-flight-deck/agentic-os/actions/workflows/release.yml/dispatches",
    ]
    assert calls[2][2] == b'{"ref": "issue-473"}'


def test_rerun_failed_jobs_dispatches_the_workflow_when_the_web_route_is_unavailable(monkeypatch):
    calls: list[tuple[str, str, bytes | None]] = []

    def fake_request(url, token, *, data=None, content_type=None, auth_scheme="basic"):
        calls.append((url, token, data))
        if data is None:
            if url.endswith("/api/v1/repos/coilyco-flight-deck/agentic-os/actions/runs/7917"):
                return json.dumps(RUN_METADATA).encode("utf-8")
            return RUN_PAGE_HTML.encode("utf-8")
        return b""

    monkeypatch.setattr(rerun, "request", fake_request)

    rc = rerun.main(["rerun-failed-jobs", "coilyco-flight-deck", "agentic-os", "1243"])

    assert rc == 0
    assert [url for url, _token, _data in calls] == [
        "https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/actions/runs/1243",
        "https://forgejo.coilysiren.me/api/v1/repos/coilyco-flight-deck/agentic-os/actions/runs/7917",
        "https://forgejo.coilysiren.me/api/v1/repos/coilyco-flight-deck/agentic-os/actions/workflows/release.yml/dispatches",
    ]
    assert calls[2][2] == b'{"ref": "issue-473"}'

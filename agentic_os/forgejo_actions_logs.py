"""Forgejo Actions log bridge over the UI log-cursor route.

The documented API log route (`/api/v1/.../actions/runs/{run_id}/jobs/{job_id}
/attempt/{n}/logs`) 404s on Forgejo 15 even for fresh, successful runs
(aos#476), so this bridge speaks the route the web UI itself uses: GET the job
page for its embedded initial payload (the step list), then POST `logCursors`
to the same URL to stream every step's lines. The `/attempt/{n}` segment is
required - without it the handler resolves attempt 0 and reports the task
missing.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import urllib.error

from agentic_os.forgejo_actions_web import (
    ForgejoActionsWebError,
    extract_initial_post_response,
    request,
)

DEFAULT_BASE_URL = "https://forgejo.coilysiren.me"


@dataclasses.dataclass(frozen=True)
class JobLogTarget:
    owner: str
    repo: str
    run_index: int
    job_index: int
    attempt: int

    def page_url(self, base_url: str) -> str:
        return (
            f"{base_url}/{self.owner}/{self.repo}/actions/runs/"
            f"{self.run_index}/jobs/{self.job_index}/attempt/{self.attempt}"
        )


class ForgejoActionsLogError(RuntimeError):
    """The bridge could not resolve or fetch the requested log stream."""


def parse_job_steps(page_html: str, *, page_url: str) -> list[dict]:
    """Extract the current job's step list from the page's initial payload."""
    try:
        decoded = extract_initial_post_response(page_html, page_url=page_url)
    except ForgejoActionsWebError as exc:
        raise ForgejoActionsLogError(str(exc)) from exc
    steps = decoded.get("state", {}).get("currentJob", {}).get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise ForgejoActionsLogError(
            f"Forgejo job page exposed no steps for this job. target_url={page_url}"
        )
    return steps


def log_cursor_body(step_count: int) -> bytes:
    """The UI's log request: one expanded null cursor per step fetches everything."""
    cursors = [{"step": i, "cursor": None, "expanded": True} for i in range(step_count)]
    return json.dumps({"logCursors": cursors}).encode("utf-8")


def render_step_logs(steps: list[dict], response: dict) -> str:
    """Interleave step headers with their fetched lines, in step order."""
    by_step: dict[int, list[str]] = {}
    for entry in (response.get("logs", {}) or {}).get("stepsLog", []) or []:
        lines = [line.get("message", "") for line in entry.get("lines", []) or []]
        by_step[int(entry.get("step", -1))] = lines
    out: list[str] = []
    for i, step in enumerate(steps):
        summary = step.get("summary", f"step {i}")
        status = step.get("status", "unknown")
        out.append(f"### step {i}: {summary} [{status}]")
        out.extend(by_step.get(i, []))
    return "\n".join(out) + "\n"


def fetch_job_logs(target: JobLogTarget, *, token: str, base_url: str) -> str:
    url = target.page_url(base_url)
    page = request(url, token).decode("utf-8", "replace")
    steps = parse_job_steps(page, page_url=url)
    body = request(url, token, data=log_cursor_body(len(steps)), content_type="application/json")
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ForgejoActionsLogError(f"unreadable log-cursor response. target_url={url}") from exc
    return render_step_logs(steps, decoded)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="actions logs",
        description="Stream a Forgejo Actions job log from a status target URL.",
    )
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("run_index", type=int)
    parser.add_argument("job_index", type=int)
    parser.add_argument("attempt", type=int, nargs="?", default=1)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    token = os.environ.get("FORGEJO_TOKEN")
    if not token:
        print("FORGEJO_TOKEN is required", file=sys.stderr)
        return 1

    base_url = os.environ.get("FORGEJO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    target = JobLogTarget(
        owner=args.owner,
        repo=args.repo,
        run_index=args.run_index,
        job_index=args.job_index,
        attempt=args.attempt,
    )
    try:
        rendered = fetch_job_logs(target, token=token, base_url=base_url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(
                "Forgejo returned 404 for the job page. Check the run/job indexes; "
                f"next usable command: {target.page_url(base_url)}",
                file=sys.stderr,
            )
            return 65
        # The instance answers a purged task with an error body, not a clean 404.
        print(
            f"Forgejo refused the log fetch ({exc.code}). Logs for finished runs are "
            "purged aggressively on this deployment (infrastructure#545), so an older "
            f"run may simply be gone. target_url={target.page_url(base_url)}",
            file=sys.stderr,
        )
        return 65
    except (OSError, ForgejoActionsLogError) as exc:
        print(str(exc), file=sys.stderr)
        return 65

    # Bytes, not str: log content is arbitrary UTF-8 and a cp1252 console
    # (Windows) must not be able to crash the bridge on an emoji.
    sys.stdout.buffer.write(rendered.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

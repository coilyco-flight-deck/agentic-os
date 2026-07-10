"""Forgejo Actions log bridge for status target URLs.

The visible PR status target uses the repository run index and the job index,
for example `/actions/runs/886/jobs/0`. Forgejo's logs route needs the internal
run id and job id, so this bridge resolves the HTML job page first, extracts the
real ids, then fetches the plaintext log stream.
"""

from __future__ import annotations

import argparse
import dataclasses
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://forgejo.coilysiren.me"
RUN_INDEX_RE = re.compile(r'data-run-index="(?P<run_index>\d+)"')
RUN_ID_RE = re.compile(r'data-run-id="(?P<run_id>\d+)"')
JOB_INDEX_RE = re.compile(r'data-job-index="(?P<job_index>\d+)"')
ATTEMPT_RE = re.compile(r'data-attempt-number="(?P<attempt>\d+)"')
INITIAL_POST_RE = re.compile(
    r'data-initial-post-response="(?P<payload>.*?)"\s*data-initial-artifacts-response=',
    re.DOTALL,
)


@dataclasses.dataclass(frozen=True)
class JobLogTarget:
    owner: str
    repo: str
    run_index: int
    job_index: int
    attempt: int
    run_id: int
    job_id: int

    def page_url(self, base_url: str) -> str:
        return (
            f"{base_url}/{self.owner}/{self.repo}/actions/runs/"
            f"{self.run_index}/jobs/{self.job_index}/attempt/{self.attempt}"
        )

    def logs_url(self, base_url: str) -> str:
        return (
            f"{base_url}/api/v1/repos/{self.owner}/{self.repo}/actions/runs/"
            f"{self.run_id}/jobs/{self.job_id}/attempt/{self.attempt}/logs"
        )


class ForgejoActionsLogError(RuntimeError):
    """The bridge could not resolve or fetch the requested log stream."""


def _http_get(url: str, token: str, accept: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.read()


def _parse_job_page(
    target: JobLogTarget, page_html: str, *, base_url: str
) -> JobLogTarget:
    run_index_match = RUN_INDEX_RE.search(page_html)
    run_id_match = RUN_ID_RE.search(page_html)
    job_index_match = JOB_INDEX_RE.search(page_html)
    attempt_match = ATTEMPT_RE.search(page_html)
    payload_match = INITIAL_POST_RE.search(page_html)
    if not all((run_index_match, run_id_match, job_index_match, attempt_match, payload_match)):
        raise ForgejoActionsLogError(
            "could not resolve Forgejo job ids from the HTML job page. "
            f"target_url={target.page_url(base_url)}"
        )

    if int(run_index_match.group("run_index")) != target.run_index:
        raise ForgejoActionsLogError(
            "Forgejo job page did not match the requested run index. "
            f"target_url={target.page_url(base_url)}"
        )
    if int(job_index_match.group("job_index")) != target.job_index:
        raise ForgejoActionsLogError(
            "Forgejo job page did not match the requested job index. "
            f"target_url={target.page_url(base_url)}"
        )

    payload = html.unescape(payload_match.group("payload"))
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ForgejoActionsLogError(
            "Forgejo returned an unreadable job page payload. "
            f"target_url={target.page_url(base_url)}"
        ) from exc

    run = decoded.get("state", {}).get("run", {})
    jobs = run.get("jobs", [])
    if not isinstance(jobs, list) or target.job_index >= len(jobs):
        raise ForgejoActionsLogError(
            "Forgejo job page did not expose the requested job index. "
            f"target_url={target.page_url(base_url)}"
        )

    job = jobs[target.job_index]
    try:
        run_id = int(run_id_match.group("run_id"))
        job_id = int(job["id"])
        attempt = int(attempt_match.group("attempt"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ForgejoActionsLogError(
            "Forgejo job page exposed an incomplete job mapping. "
            f"target_url={target.page_url(base_url)}"
        ) from exc

    return dataclasses.replace(target, run_id=run_id, job_id=job_id, attempt=attempt)


def resolve_target(
    owner: str,
    repo: str,
    run_index: int,
    job_index: int,
    attempt: int,
    *,
    token: str,
    base_url: str = DEFAULT_BASE_URL,
) -> JobLogTarget:
    target = JobLogTarget(
        owner=owner,
        repo=repo,
        run_index=run_index,
        job_index=job_index,
        attempt=attempt,
        run_id=run_index,
        job_id=job_index,
    )
    page_html = _http_get(target.page_url(base_url), token, "text/html").decode(
        "utf-8", "replace"
    )
    resolved = _parse_job_page(target, page_html, base_url=base_url)
    return resolved


def fetch_logs(target: JobLogTarget, *, token: str, base_url: str) -> bytes:
    return _http_get(target.logs_url(base_url), token, "text/plain")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="actions logs",
        description="Stream a Forgejo Actions job log from a status target URL.",
    )
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("run_index", type=int)
    parser.add_argument("job_index", type=int)
    parser.add_argument("attempt", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    token = os.environ.get("FORGEJO_TOKEN")
    if not token:
        print("FORGEJO_TOKEN is required", file=sys.stderr)
        return 1

    base_url = os.environ.get("FORGEJO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    status_target = JobLogTarget(
        owner=args.owner,
        repo=args.repo,
        run_index=args.run_index,
        job_index=args.job_index,
        attempt=args.attempt,
        run_id=args.run_index,
        job_id=args.job_index,
    )
    try:
        target = resolve_target(
            args.owner,
            args.repo,
            args.run_index,
            args.job_index,
            args.attempt,
            token=token,
            base_url=base_url,
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(
                "Forgejo returned 404 for the HTML job page that should resolve "
                f"status target /actions/runs/{args.run_index}/jobs/{args.job_index}. "
                "The bridge needs that page to map the visible run index and job "
                "index to the internal run id and job id. "
                f"next usable command: {status_target.page_url(base_url)}",
                file=sys.stderr,
            )
            return 65
        raise
    except (OSError, ForgejoActionsLogError) as exc:
        print(str(exc), file=sys.stderr)
        return 65

    try:
        logs = fetch_logs(target, token=token, base_url=base_url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(
                "Forgejo returned 404 for the resolved job log route. "
                f"status target /actions/runs/{args.run_index}/jobs/{args.job_index} "
                f"resolved to run_id={target.run_id} job_id={target.job_id}. "
                f"next usable command: {status_target.page_url(base_url)}",
                file=sys.stderr,
            )
            return 65
        raise
    except (OSError, ForgejoActionsLogError) as exc:
        print(str(exc), file=sys.stderr)
        return 65

    sys.stdout.buffer.write(logs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Forgejo Actions rerun bridge for status-target rerun verbs.

The web rerun controls are not universally exposed on this Forgejo deployment.
When a run cannot be re-run in place, the bridge falls back to dispatching the
workflow file again for the same ref.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import os
import sys
import urllib.error
import urllib.parse

from agentic_os.forgejo_actions_web import (
    ForgejoActionsWebError,
    extract_initial_post_response,
    request,
)

DEFAULT_BASE_URL = "https://forgejo.coilysiren.me"
RUN_ID_RE = re.compile(r'data-run-id="(?P<run_id>\d+)"')


@dataclasses.dataclass(frozen=True)
class RerunTarget:
    owner: str
    repo: str
    run_index: str

    def page_url(self, base_url: str) -> str:
        return f"{base_url}/{self.owner}/{self.repo}/actions/runs/{self.run_index}"


class ForgejoActionsRerunError(RuntimeError):
    """The bridge could not resolve the rerun target."""


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="actions rerun",
        description="Rerun a Forgejo Actions workflow run by its visible run id.",
    )
    parser.add_argument("mode", choices=["rerun", "rerun-failed-jobs"])
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("run_id")
    return parser.parse_args(argv)


def _fetch_run_state(run_page_url: str, *, token: str) -> tuple[dict, str]:
    page = request(run_page_url, token).decode("utf-8", "replace")
    try:
        decoded = extract_initial_post_response(page, page_url=run_page_url)
    except ForgejoActionsWebError as exc:
        raise ForgejoActionsRerunError(str(exc)) from exc
    run_id_match = RUN_ID_RE.search(page)
    if not run_id_match:
        raise ForgejoActionsRerunError(f"Forgejo page exposed no run id. target_url={run_page_url}")
    run = decoded.get("state", {}).get("run", {})
    if not run:
        raise ForgejoActionsRerunError(f"Forgejo page exposed no run state. target_url={run_page_url}")
    return run, run_id_match.group("run_id")


def _fetch_run_metadata(api_url: str, *, token: str) -> dict:
    try:
        body = request(api_url, token, auth_scheme="token")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ForgejoActionsRerunError(f"Forgejo returned 404 for the run metadata route. target_url={api_url}") from exc
        raise
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ForgejoActionsRerunError(f"Forgejo returned unreadable run metadata. target_url={api_url}") from exc


def _dispatch_ref(event_payload: str) -> str:
    payload = json.loads(event_payload)
    pull_request = payload.get("pull_request", {}) if isinstance(payload, dict) else {}
    head = pull_request.get("head", {}) if isinstance(pull_request, dict) else {}
    ref = head.get("ref") or payload.get("head_branch") or payload.get("ref")
    if isinstance(ref, str) and ref.startswith("refs/heads/"):
        ref = ref.removeprefix("refs/heads/")
    if not ref:
        raise ForgejoActionsRerunError("Forgejo run metadata did not include a dispatch ref.")
    return ref


def _dispatch_workflow(
    *,
    base_url: str,
    owner: str,
    repo: str,
    workflow_id: str,
    ref: str,
    token: str,
) -> bytes:
    workflow = urllib.parse.quote(workflow_id, safe="")
    dispatch_url = f"{base_url}/api/v1/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"
    payload = json.dumps({"ref": ref}).encode("utf-8")
    return request(dispatch_url, token, data=payload, content_type="application/json", auth_scheme="token")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    token = os.environ.get("FORGEJO_TOKEN")
    if not token:
        print("FORGEJO_TOKEN is required", file=sys.stderr)
        return 1

    base_url = os.environ.get("FORGEJO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    target = RerunTarget(owner=args.owner, repo=args.repo, run_index=args.run_id)
    run_page_url = target.page_url(base_url)

    try:
        run, run_id = _fetch_run_state(run_page_url, token=token)
        api_url = f"{base_url}/api/v1/repos/{args.owner}/{args.repo}/actions/runs/{run_id}"
        metadata = _fetch_run_metadata(api_url, token=token)
        workflow_id = metadata.get("workflow_id")
        if not workflow_id:
            raise ForgejoActionsRerunError(f"Forgejo run metadata exposed no workflow id. target_url={api_url}")
        ref = _dispatch_ref(metadata.get("event_payload", "{}"))

        if args.mode == "rerun" and run.get("canRerun", False):
            try:
                payload = request(f"{base_url}{run['link']}/rerun", token, data=b"", content_type="application/json")
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                payload = _dispatch_workflow(
                    base_url=base_url,
                    owner=args.owner,
                    repo=args.repo,
                    workflow_id=str(workflow_id),
                    ref=ref,
                    token=token,
                )
        else:
            if args.mode == "rerun-failed-jobs":
                failed_jobs = [
                    (index, job)
                    for index, job in enumerate(run.get("jobs", []))
                    if job.get("status") == "failure" and job.get("canRerun", True)
                ]
                if not failed_jobs:
                    print(
                        "Forgejo exposed no failed jobs that can be rerun, so dispatching the workflow instead. "
                        f"target_url={run_page_url}",
                        file=sys.stderr,
                    )
            payload = _dispatch_workflow(
                base_url=base_url,
                owner=args.owner,
                repo=args.repo,
                workflow_id=str(workflow_id),
                ref=ref,
                token=token,
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(
                "Forgejo returned 404 for the rerun route. "
                f"target_url={run_page_url}",
                file=sys.stderr,
            )
            return 65
        print(
            f"Forgejo refused the rerun fetch ({exc.code}). target_url={run_page_url}",
            file=sys.stderr,
        )
        return 65
    except (OSError, ForgejoActionsWebError, ForgejoActionsRerunError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 65

    if payload:
        sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

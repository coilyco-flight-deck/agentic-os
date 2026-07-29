#!/usr/bin/env python3
"""Post a Telegram alert for a failing CI job on main."""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def build_message(repo: str, workflow: str, job: str, ref: str, sha: str, run_url: str) -> str:
    return "\n".join(
        [
            "CI failed on main",
            f"repo: {repo}",
            f"workflow: {workflow}",
            f"job: {job}",
            f"ref: {ref}",
            f"sha: {sha}",
            f"run: {run_url}",
        ]
    )


def send_message(
    bot_token: str,
    chat_id: str,
    message: str,
    api_base: str,
    proxy_url: str,
) -> None:
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    url = f"{api_base.rstrip('/')}/bot{bot_token}/sendMessage"
    req = urllib.request.Request(url, data=payload, method="POST")
    proxy_handler = (
        urllib.request.ProxyHandler({"https": proxy_url})
        if proxy_url
        else urllib.request.ProxyHandler()
    )
    opener = urllib.request.build_opener(proxy_handler)
    with opener.open(req, timeout=15) as resp:
        resp.read()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bot-token", default=os.environ.get("BOT_TOKEN", ""))
    ap.add_argument("--chat-id", default=os.environ.get("CHAT_ID", ""))
    ap.add_argument("--repo", default=os.environ.get("REPO", ""))
    ap.add_argument("--workflow", default=os.environ.get("WORKFLOW", ""))
    ap.add_argument("--job", default=os.environ.get("JOB", ""))
    ap.add_argument("--ref", default=os.environ.get("REF", ""))
    ap.add_argument("--sha", default=os.environ.get("SHA", ""))
    ap.add_argument("--run-url", default=os.environ.get("RUN_URL", ""))
    ap.add_argument("--api-base", default=os.environ.get("API_BASE", "https://api.telegram.org"))
    ap.add_argument(
        "--proxy-url",
        default=os.environ.get("FORGEJO_EGRESS_PROXY", "").strip(),
    )
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    missing = [
        name
        for name, value in {
            "bot-token": args.bot_token,
            "chat-id": args.chat_id,
            "repo": args.repo,
            "workflow": args.workflow,
            "job": args.job,
            "ref": args.ref,
            "sha": args.sha,
            "run-url": args.run_url,
        }.items()
        if not value
    ]
    if missing:
        print(f"missing required inputs: {', '.join(missing)}", file=sys.stderr)
        return 2

    message = build_message(args.repo, args.workflow, args.job, args.ref, args.sha, args.run_url)
    if args.dry_run or args.api_base == "dry-run":
        print(message)
        return 0

    try:
        send_message(
            args.bot_token,
            args.chat_id,
            message,
            args.api_base,
            args.proxy_url,
        )
    except urllib.error.URLError as exc:
        print(
            f"telegram alert failed ({type(exc).__name__})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

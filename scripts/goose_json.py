#!/usr/bin/env python3
"""goose-json: run a Goose call with an enforced JSON-schema response and return
the parsed, validated object - the single structured-output boundary the triage
tooling (and any future caller) goes through instead of regex-scraping stdout.

Enforcement is real, not prompt-coaxed: the prompt and the response JSON schema
are written into a temp Goose recipe, and `goose run --recipe ... --output-format
json` makes the provider constrain the model's reply to that schema. The reply
comes back inside Goose's JSON envelope, so parsing is two json.loads (envelope,
then the assistant message's text) - no fences, no last-line heuristics.

As a module:  from goose_json import ask;  ask(prompt, schema) -> dict | None
As the ward verb `goose-json`:  --schema FILE (--text STR | --prompt-file FILE)
prints the validated object to stdout, or exits non-zero on failure.

See docs/goose-triage.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

GOOSE_BASE = ["goose", "run", "--no-profile", "--quiet", "--no-session",
              "--max-turns", "1", "--output-format", "json"]

# failure-record schema v1: one classified JSON line per genuine ask() failure,
# appended to a per-repo local buffer. See docs/goose-failure-records.md.
FAILURE_DIR = Path.home() / ".cache" / "agentic-os" / "tool-failures"
STDERR_EXCERPT_MAX = 2000  # cap the discarded-evidence tail we keep per record


def ask(prompt: str, schema: dict, timeout: int = 120, retries: int = 2,
        repo: str | None = None, label: str | None = None) -> dict | None:
    """Run one enforced-JSON Goose call; return the validated object or None.

    Every failure path now writes one classified failure-record (schema v1) to
    the per-repo buffer instead of discarding `.returncode` / `.stderr`. `repo`
    keys the buffer (defaults to the current git origin slug); `label` names the
    call site (the per-pass "tool" analog) and feeds the fingerprint."""
    repo = repo or _repo_slug()
    title = label or schema.get("title") or "goose-json"
    recipe = {
        "version": "1.0.0",
        "title": "goose-json",
        "description": "enforced JSON-schema response",
        "instructions": "Answer the prompt. Reply only with data conforming to the response schema - no preamble.",
        "prompt": prompt,
        "response": {"json_schema": schema},
    }
    fd, path = tempfile.mkstemp(suffix=".yaml", prefix="goose-json-")
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(recipe, f, sort_keys=False)
    last_exit: int | None = None
    last_stderr = ""
    try:
        for attempt in range(retries):
            try:
                proc = subprocess.run(GOOSE_BASE + ["--recipe", path],
                                      capture_output=True, text=True,
                                      timeout=timeout)
            except subprocess.TimeoutExpired:
                _record_failure(repo, title, "timeout", None, attempt, "",
                                f"goose run timed out after {timeout}s")
                last_exit, last_stderr = None, ""
                continue
            obj, parse_class, detail = _parse(proc.stdout, schema)
            if obj is not None:
                return obj
            # Failed attempt - returncode is the strongest signal (provider 5xx /
            # rate-limit / panic surface here), else the parse-failure reason.
            last_exit, last_stderr = proc.returncode, proc.stderr
            if proc.returncode != 0:
                _record_failure(repo, title, "nonzero_exit", proc.returncode,
                                attempt, proc.stderr, f"goose exited {proc.returncode}")
            else:
                _record_failure(repo, title, parse_class, proc.returncode,
                                attempt, proc.stderr, detail)
        _record_failure(repo, title, "exhausted_retries", last_exit, retries - 1,
                        last_stderr, f"all {retries} attempt(s) failed")
        return None
    finally:
        os.unlink(path)


def _parse(envelope_text: str, schema: dict) -> tuple[dict | None, str, str]:
    """Pull the schema-valid object out of Goose's --output-format json envelope:
    the last assistant message whose text json-parses and satisfies the schema.

    Returns (obj, failure_class, detail). On success obj is the object and the
    other two are empty; on failure obj is None and failure_class is one of
    `bad_envelope` (the envelope itself did not JSON-parse) or
    `no_schema_valid_message` (it parsed but nothing satisfied the schema)."""
    try:
        env = json.loads(envelope_text)
    except json.JSONDecodeError as e:
        return None, "bad_envelope", f"envelope not JSON: {e}"
    for msg in reversed(env.get("messages") or []):
        if msg.get("role") != "assistant":
            continue
        for chunk in msg.get("content") or []:
            text = chunk.get("text")
            if not text:
                continue
            try:
                obj = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                continue
            if _satisfies(obj, schema):
                return obj, "", ""
    return None, "no_schema_valid_message", "no assistant message satisfied the schema"


_REPO_SLUG_CACHE: list[str] = []


def _repo_slug() -> str:
    """Slug (owner/name) of the current git origin, cached for the process;
    "unknown" when no origin resolves. Keys the per-repo failure buffer."""
    if not _REPO_SLUG_CACHE:
        slug = "unknown"
        try:
            url = subprocess.run(["git", "remote", "get-url", "origin"],
                                 capture_output=True, text=True, timeout=10).stdout.strip()
            if url:
                u = url[:-4] if url.endswith(".git") else url
                u = u.split("://", 1)[-1].split("@", 1)[-1].replace(":", "/", 1)
                parts = [p for p in u.split("/") if p]
                if len(parts) >= 2:
                    slug = "/".join(parts[-2:])
        except (OSError, subprocess.SubprocessError):
            pass
        _REPO_SLUG_CACHE.append(slug)
    return _REPO_SLUG_CACHE[0]


def _stderr_signature(stderr: str) -> str:
    """Normalize Goose stderr to a stable signature so a flood of identical
    failures collapses to one fingerprint: strip hex / paths / digits / dates,
    fold whitespace, head-truncate. Volatile tokens go, the failure shape stays."""
    s = re.sub(r"0x[0-9a-fA-F]+", "0xHEX", stderr.strip())
    s = re.sub(r"\b[0-9a-fA-F]{8,}\b", "HEX", s)
    s = re.sub(r"/\S+", "PATH", s)
    s = re.sub(r"\d+", "N", s)
    s = re.sub(r"\s+", " ", s)
    return s[:200]


def _fingerprint(failure_class: str, schema_title: str, stderr: str) -> str:
    """Collapse identical failures into one counted bucket: a short hash over
    (harness, failure_class, schema_title, normalized-stderr-signature)."""
    sig = _stderr_signature(stderr)
    blob = "\x1f".join(["goose", failure_class, schema_title, sig])
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _record_failure(repo: str, schema_title: str, failure_class: str,
                    exit_code: int | None, attempt: int, stderr: str,
                    detail: str) -> None:
    """Append one failure-record (schema v1) to ~/.cache/agentic-os/tool-failures/
    <repo-slug>.jsonl. Best-effort: instrumentation must never break the call path,
    so any write error is swallowed."""
    excerpt = stderr.strip()
    if len(excerpt) > STDERR_EXCERPT_MAX:
        excerpt = "..." + excerpt[-STDERR_EXCERPT_MAX:]
    record = {
        "ts": int(time.time()),
        "harness": "goose",
        "source": "goose_json.ask",
        "repo": repo,
        "failure_class": failure_class,
        "schema_title": schema_title,
        "exit_code": exit_code,
        "attempt": attempt,
        "stderr_excerpt": excerpt,
        "detail": detail,
        "fingerprint": _fingerprint(failure_class, schema_title, stderr),
    }
    try:
        FAILURE_DIR.mkdir(parents=True, exist_ok=True)
        path = FAILURE_DIR / f"{repo.replace('/', '-')}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # a failed failure-write must not mask the underlying Goose failure


def _satisfies(obj, schema: dict) -> bool:
    """Lightweight backstop check (Goose already enforced via the provider):
    required keys present, and top-level type matches when the schema names one."""
    want = schema.get("type")
    if want == "object" and not isinstance(obj, dict):
        return False
    if want == "array" and not isinstance(obj, list):
        return False
    if isinstance(obj, dict):
        return all(k in obj for k in schema.get("required", []))
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Enforced JSON-schema Goose call.")
    ap.add_argument("--schema", required=True, help="path to a JSON-schema file for the response")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="the prompt text")
    src.add_argument("--prompt-file", help="path to a file holding the prompt")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args(argv)

    schema = json.loads(open(args.schema, encoding="utf-8").read())
    prompt = args.text if args.text is not None else open(args.prompt_file, encoding="utf-8").read()

    obj = ask(prompt, schema, timeout=args.timeout)
    if obj is None:
        print("goose-json: no schema-valid response from Goose", file=sys.stderr)
        return 1
    print(json.dumps(obj))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

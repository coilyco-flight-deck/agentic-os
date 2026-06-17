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
import json
import os
import subprocess
import sys
import tempfile

import yaml

GOOSE_BASE = ["goose", "run", "--no-profile", "--quiet", "--no-session",
              "--max-turns", "1", "--output-format", "json"]


def ask(prompt: str, schema: dict, timeout: int = 120, retries: int = 2) -> dict | None:
    """Run one enforced-JSON Goose call; return the validated object or None."""
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
    try:
        for _ in range(retries):
            try:
                out = subprocess.run(GOOSE_BASE + ["--recipe", path],
                                     capture_output=True, text=True,
                                     timeout=timeout).stdout
            except subprocess.TimeoutExpired:
                continue
            obj = _parse(out, schema)
            if obj is not None:
                return obj
        return None
    finally:
        os.unlink(path)


def _parse(envelope_text: str, schema: dict) -> dict | None:
    """Pull the schema-valid object out of Goose's --output-format json envelope:
    the last assistant message whose text json-parses and satisfies the schema."""
    try:
        env = json.loads(envelope_text)
    except json.JSONDecodeError:
        return None
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
                return obj
    return None


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

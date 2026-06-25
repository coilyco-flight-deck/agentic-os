#!/usr/bin/env python3
"""claude-judge: a goose-json-contract judge backed by the `claude` CLI.

The drop-in stronger judge for goose-triage (coilyco-flight-deck/agentic-os#271).
It speaks the exact same CLI contract as the `goose-json` verb -

    claude_judge.py --schema FILE (--text STR | --prompt-file FILE)

prints one schema-valid JSON object to stdout, exits non-zero on failure - so the
triage `command` engine drives it with no special-casing. Where goose-json runs a
local Goose recipe, this runs `claude -p ... --output-format json` and pulls the
model's reply out of the result envelope.

Goose enforces the response schema at the provider; the `claude` CLI does not, so
this asks for strict JSON in the prompt, then extracts and validates: strip an
optional code fence, json-parse, check the schema's required keys (the same
lightweight backstop `goose_json` uses). An unparseable or non-conforming reply
is a non-zero exit, which the command engine reads as a failed judgment and falls
back to the pipeline's per-pass default - identical to a Goose-call failure.

Usage as a triage engine:
    ward exec goose-triage -- --engine claude
which is sugar for `--engine command --engine-cmd "uv run python scripts/claude_judge.py"`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goose_json import _satisfies  # the same required-keys backstop the goose path uses

# Default to the strongest readily-available judge; overridable so a run can pin a
# cheaper or a specific model. An alias ("opus"/"sonnet") or a full id both work.
DEFAULT_MODEL = "opus"

_INSTRUCTION = (
    "Reply with ONLY a single JSON object that conforms to this JSON schema. "
    "No prose, no explanation, no markdown code fence - just the raw JSON object.\n"
    "Schema:\n{schema}\n\nTask:\n{prompt}"
)


def _extract_json(text: str) -> object | None:
    """Pull a JSON object out of a model reply: try a direct parse, then strip a
    ```json fence, then fall back to the first balanced {...} span. Returns the
    parsed value or None when nothing parses."""
    text = (text or "").strip()
    if not text:
        return None
    for candidate in _candidates(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _candidates(text: str):
    """Yield decreasingly-trusting slices of a reply to try json.loads on."""
    yield text
    # Fenced block: ```json ... ``` or ``` ... ```
    if "```" in text:
        inner = text.split("```", 2)
        if len(inner) >= 2:
            body = inner[1]
            if body.lstrip().lower().startswith("json"):
                body = body.lstrip()[4:]
            yield body.strip()
    # First balanced object span, for a reply wrapped in prose.
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    yield text[start:i + 1]
                    break


def _claude_result(stdout: str) -> str | None:
    """Pull the assistant's final text out of `claude --output-format json`'s
    result envelope ({"type":"result","result":"...",...}). Returns None when the
    envelope itself does not parse or carries no string result."""
    try:
        env = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    result = env.get("result") if isinstance(env, dict) else None
    return result if isinstance(result, str) else None


def judge(prompt: str, schema: dict, model: str = DEFAULT_MODEL,
          timeout: int = 120) -> dict | None:
    """One claude-CLI judgment under the goose-json contract: build the strict-JSON
    prompt, run `claude -p ... --output-format json`, extract and validate the
    reply. Returns the validated object or None on any failure."""
    full = _INSTRUCTION.format(schema=json.dumps(schema), prompt=prompt)
    cmd = ["claude", "-p", full, "--output-format", "json", "--model", model]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    text = _claude_result(proc.stdout)
    if text is None:
        return None
    obj = _extract_json(text)
    if isinstance(obj, dict) and _satisfies(obj, schema):
        return obj
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Claude-CLI judge over the goose-json contract.")
    ap.add_argument("--schema", required=True, help="path to a JSON-schema file for the response")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="the prompt text")
    src.add_argument("--prompt-file", help="path to a file holding the prompt")
    ap.add_argument("--model", default=DEFAULT_MODEL, help='claude model alias or id (default "opus")')
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args(argv)

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    prompt = args.text if args.text is not None else Path(args.prompt_file).read_text(encoding="utf-8")

    obj = judge(prompt, schema, model=args.model, timeout=args.timeout)
    if obj is None:
        print("claude-judge: no schema-valid response from claude", file=sys.stderr)
        return 1
    print(json.dumps(obj))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

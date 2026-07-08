#!/usr/bin/env python3
"""Pluggable judgment engines for goose-triage.

The triage pipeline routes every per-issue judgment - P0 confirm, urgency,
run-off, mode - through one seam: a callable

    ask(prompt, schema, *, repo=..., label=...) -> dict | None

Everything around that seam (the P0 regex net, the percentile cut, the
idempotent labels, the create-if-absent verdict comment) is engine-agnostic
deterministic scaffolding. This module makes the seam swappable so the same
audited scaffolding can run behind a judge stronger than the default local
Goose + qwen3-coder:30b - without hand-rolling the pipeline (the motivating
papercut in the engine-triage flow).

Built-in engines:

  - `goose-json` (default): the local Goose harness via `goose_json.ask`. The
    provider enforces the response schema; failures are classified and buffered.
  - `command`: shell out to ANY external judge implementing the goose-json CLI
    contract - `<cmd> --schema FILE --prompt-file FILE` prints one schema-valid
    JSON object to stdout, non-zero exit on failure. A cloud-model judge is just
    such a command, so a stronger judge needs no change here: point `--engine-cmd`
    at its wrapper. Any failure (non-zero exit, unparseable stdout, schema
    mismatch) returns None, so the pipeline's fail-soft defaults apply uniformly
    across every engine.
  - `claude`: turn-key sugar for `command` pointed at `scripts/claude_judge.py`,
    the bundled Claude-CLI judge. `--engine claude` re-triages with the live
    Claude model and no extra wiring.

See docs/goose-triage.md.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Reuse goose_json's lightweight schema backstop so the command engine validates
# an external judge's reply the same way the goose path validates Goose's.
from goose_json import _satisfies, ask as _goose_ask

SCRIPTS_DIR = Path(__file__).resolve().parent

# Default attribution names the local Goose harness; each engine carries its own
# so the report line and verdict-comment footer name the judge that actually ran.
DEFAULT_ATTRIBUTION = "Goose (qwen3-coder:30b)"

# The bundled Claude-CLI judge, run with the current interpreter (already the ward
# venv under `ward exec`; claude_judge needs only stdlib), so `claude` is turn-key.
CLAUDE_JUDGE_CMD = [sys.executable, str(SCRIPTS_DIR / "claude_judge.py")]

AskFn = Callable[..., "dict | None"]


@dataclass(frozen=True)
class Engine:
    """One pluggable judgment engine: a stable name, the human-readable
    attribution that names the judge in the report and comment footer, and the
    `ask` callable the pipeline drives through its single seam."""

    name: str
    attribution: str
    ask: AskFn


def _command_ask(cmd: list[str], prompt: str, schema: dict, timeout: int = 120,
                 repo: str | None = None, label: str | None = None) -> dict | None:
    """Run one external-judge call over the goose-json CLI contract; return the
    validated object or None.

    The command receives the prompt and the response JSON schema as temp files
    (`--schema FILE --prompt-file FILE`, exactly the `goose-json` verb's own
    interface) and must print one JSON object to stdout, exiting non-zero on
    failure. Mirrors `goose_json.ask`'s dict|None contract so the pipeline's
    fail-soft defaults apply to a stronger judge the same as to Goose. `repo` /
    `label` are accepted for seam compatibility; an external judge owns its own
    failure recording, so they are not forwarded."""
    sfd, spath = tempfile.mkstemp(suffix=".json", prefix="triage-schema-")
    pfd, ppath = tempfile.mkstemp(suffix=".txt", prefix="triage-prompt-")
    try:
        with os.fdopen(sfd, "w") as f:
            json.dump(schema, f)
        with os.fdopen(pfd, "w") as f:
            f.write(prompt)
        try:
            proc = subprocess.run(cmd + ["--schema", spath, "--prompt-file", ppath],
                                  capture_output=True, text=True, timeout=timeout)
        except (subprocess.TimeoutExpired, OSError):
            return None
        if proc.returncode != 0:
            return None
        out = (proc.stdout or "").strip()
        if not out:
            return None
        try:
            obj = json.loads(out)
        except json.JSONDecodeError:
            return None
        return obj if _satisfies(obj, schema) else None
    finally:
        os.unlink(spath)
        os.unlink(ppath)


def make_command_engine(cmd: list[str], attribution: str | None = None,
                        name: str = "command") -> Engine:
    """Build a `command` engine bound to `cmd` (already split into argv). The
    attribution defaults to the command string when not given explicitly."""
    attr = attribution or " ".join(cmd)

    def ask(prompt: str, schema: dict, timeout: int = 120, retries: int = 2,
            repo: str | None = None, label: str | None = None) -> dict | None:
        # `retries` is part of the seam signature (goose_json.ask has it); an
        # external judge owns its own retry policy, so it is accepted and ignored.
        return _command_ask(cmd, prompt, schema, timeout=timeout, repo=repo, label=label)

    return Engine(name=name, attribution=attr, ask=ask)


def goose_json_engine() -> Engine:
    """The default engine: the local Goose + qwen3-coder:30b harness."""
    return Engine(name="goose-json", attribution=DEFAULT_ATTRIBUTION, ask=_goose_ask)


# Engine names selectable via --engine / AOS_TRIAGE_ENGINE. `command` and `claude`
# resolve through select_engine (they need the cmd / a default attribution).
ENGINE_NAMES = ("goose-json", "command", "claude")


def select_engine(engine: str = "goose-json", cmd: str | None = None,
                  attribution: str | None = None) -> Engine:
    """Resolve the engine name (+ optional command / attribution overrides) into
    a concrete Engine. Raises ValueError on an unknown name or a `command` engine
    with no command, so the caller can surface a clean CLI error.

    `cmd` is a shell-quoted string (from --engine-cmd or AOS_TRIAGE_ENGINE_CMD),
    split here with shlex so an operator can pass `"python my_judge.py --model x"`."""
    if engine == "goose-json":
        return goose_json_engine()
    if engine == "claude":
        return make_command_engine(CLAUDE_JUDGE_CMD,
                                   attribution=attribution or "Claude (claude CLI)",
                                   name="claude")
    if engine == "command":
        if not cmd or not cmd.strip():
            raise ValueError("--engine command needs --engine-cmd (or "
                             "AOS_TRIAGE_ENGINE_CMD): the judge command to run")
        return make_command_engine(shlex.split(cmd), attribution=attribution)
    raise ValueError(f"unknown engine {engine!r}; choose one of {', '.join(ENGINE_NAMES)}")


def select_engine_from_env(engine: str | None = None, cmd: str | None = None,
                           attribution: str | None = None) -> Engine:
    """select_engine with environment fallbacks, so the engine is selectable
    without a flag (a cron / ward-exec run can set AOS_TRIAGE_ENGINE). Explicit
    arguments win over the environment; the environment wins over the defaults."""
    engine = engine or os.environ.get("AOS_TRIAGE_ENGINE") or "goose-json"
    cmd = cmd or os.environ.get("AOS_TRIAGE_ENGINE_CMD")
    attribution = attribution or os.environ.get("AOS_TRIAGE_ENGINE_ATTRIBUTION")
    return select_engine(engine, cmd=cmd, attribution=attribution)

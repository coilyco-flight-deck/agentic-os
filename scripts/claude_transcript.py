#!/usr/bin/env python3
"""claude-drain: convert Claude Code tool-use failures into failure-records.

Claude Code hooks cannot see tool failures (verified empirically, agentic-os#249):
PostToolUse is success-only, the Bash payload carries no exit code, and some
client-validated errors (a no-match Edit) fire no hook at all. The reliable
source is the session transcript JSONL at
`~/.claude/projects/<munged-cwd>/<session-id>.jsonl`, where every tool result
carries a uniform `is_error` flag and the Bash exit code is embedded in the
error text (`Exit code N`).

This drainer sweeps those transcripts, extracts the `is_error == true` tool
results (across `user`-role `tool_result` content blocks, subagent/sidechain
transcripts included), maps each to a failure-record (schema v1, the same
contract Goose's `ask()` writes - see docs/goose-failure-records.md), and
appends it to the same per-repo buffer at
`~/.cache/agentic-os/tool-failures/<repo-slug>.jsonl`. A per-file byte-offset
watermark makes a re-sweep idempotent: only bytes appended since the last drain
are re-read, so the hot path stays decoupled and the sweep can run on a timer or
off a `SessionEnd`/`Stop` ward hook (issue C ships the buffer; no network here).

An expected-non-zero classifier marks the `grep`/`rg` no-match, `test`, `diff`,
`... || true` failures as `expected: true` so genuine failures are not buried -
the buffer keeps everything and the GlitchTip shipper (issue C) gates emission
on the genuine ones.

As a module:  from claude_transcript import drain;  drain(root) -> summary dict
As the ward verb `claude-drain`:  sweeps ~/.claude/projects, or --session <id>.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Shared schema-v1 normalizer (strip volatile tokens so identical failures share
# one fingerprint) - one source for both drains keeps the contract aligned (#249).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goose_json import _stderr_signature  # noqa: E402

PROJECTS_ROOT = Path.home() / ".claude" / "projects"
FAILURE_DIR = Path.home() / ".cache" / "agentic-os" / "tool-failures"
WATERMARK_FILE = FAILURE_DIR / ".claude-drain-watermarks.json"
STDERR_EXCERPT_MAX = 2000  # cap the error-text tail we keep per record

# Base commands whose exit 1 means "no match / differs / false", not a failure -
# the expected-non-zero set the classifier drops. Exit >= 2 stays genuine.
_EXPECTED_NONZERO_CMDS = {"grep", "rg", "egrep", "fgrep", "zgrep",
                          "test", "[", "diff", "cmp"}


# --- transcript parsing ---

def _iso_epoch(ts: str | None) -> int:
    """Best-effort ISO-8601 -> unix seconds; falls back to now() on garbage."""
    if not ts:
        return int(time.time())
    try:
        return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
    except (ValueError, TypeError):
        return int(time.time())


def _text_of(content) -> str:
    """Flatten a tool_result `content` (string, or a list of text/other blocks)
    into one string. Image blocks and non-text chunks are skipped."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for blk in content:
            if isinstance(blk, dict):
                txt = blk.get("text")
                if isinstance(txt, str) and txt:
                    parts.append(txt)
            elif isinstance(blk, str):
                parts.append(blk)
        return "\n".join(parts)
    return ""


def _last_segment(command: str) -> str:
    """The trailing pipeline/list segment whose exit code the shell reports, so
    `foo | grep bar` is judged on `grep`, not `foo`. Splits on |, &&, ||, ;."""
    seg = re.split(r"\|\||&&|[|;]", command)[-1]
    return seg.strip()


def _is_expected(tool: str, command: str, exit_code: int | None) -> bool:
    """True when a non-zero exit is the expected, benign kind: a `grep`/`rg`
    no-match (exit 1), `test`/`diff`/`cmp` reporting false/differ (exit 1), or a
    command that explicitly tolerates failure with `|| true`. Only Bash qualifies;
    every client-validated tool error is genuine."""
    if tool != "Bash" or not command:
        return False
    if re.search(r"\|\|\s*true\b", command):
        return True
    if exit_code != 1:
        return False  # exit >= 2 from grep/diff is a real error, not a no-match
    base = (_last_segment(command).split() or [""])[0]
    base = base.rsplit("/", 1)[-1]  # strip any path prefix
    return base in _EXPECTED_NONZERO_CMDS


def _classify(tool: str, text: str) -> tuple[str, int | None]:
    """Derive (failure_class, exit_code) from the tool name and error text.

    - MCP tools (`mcp__*`) -> `mcp_error`.
    - A parsed `Exit code N` (Bash) -> `nonzero_exit` with the code.
    - A `<tool_use_error>` wrapper (client-validated) -> a refined class:
      `edit_no_match`, `file_not_found`, else `tool_use_error`.
    - Anything else -> `tool_error`.
    """
    if tool.startswith("mcp__"):
        return "mcp_error", None
    m = re.search(r"Exit code (\d+)", text)
    if m:
        return "nonzero_exit", int(m.group(1))
    low = text.lower()
    if "<tool_use_error>" in low or "tool_use_error" in low:
        if "string to replace" in low or "old_string" in low or "not found in" in low:
            return "edit_no_match", None
        if "does not exist" in low or "no such file" in low or "has not been read" in low:
            return "file_not_found", None
        return "tool_use_error", None
    if "does not exist" in low or "no such file" in low:
        return "file_not_found", None
    return "tool_error", None


def _fingerprint(failure_class: str, tool: str, text: str) -> str:
    """Short hash over (harness, failure_class, tool, normalized-signature) - the
    same collapse Goose uses, so identical failures share one bucket (#249)."""
    sig = _stderr_signature(text)
    blob = "\x1f".join(["claude", failure_class, tool, sig])
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _excerpt(text: str) -> str:
    """Tail-capped error text - the evidence the failure-record carries."""
    t = text.strip()
    return ("..." + t[-STDERR_EXCERPT_MAX:]) if len(t) > STDERR_EXCERPT_MAX else t


def _records_in_file(data: bytes, watermark: int, repo: str,
                     session_fallback: str) -> list[dict]:
    """Parse one transcript's bytes into failure-records for errors appended at
    or after `watermark`. The tool-name/command map is built from the WHOLE file
    (a tool_use can predate the watermark), but only errors in the new byte range
    are emitted - that is what makes a re-sweep idempotent."""
    tool_by_id: dict[str, dict] = {}
    out: list[dict] = []
    offset = 0
    for raw in data.split(b"\n"):
        start = offset
        offset += len(raw) + 1  # +1 for the split newline
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        msg = rec.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        rtype = rec.get("type")
        if rtype == "assistant":
            for blk in content:
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tool_by_id[blk.get("id")] = {
                        "name": blk.get("name") or "unknown",
                        "input": blk.get("input") or {}}
            continue
        if rtype != "user":
            continue
        for blk in content:
            if not (isinstance(blk, dict) and blk.get("type") == "tool_result"
                    and blk.get("is_error")):
                continue
            if start < watermark:
                continue  # already drained in a prior sweep
            meta = tool_by_id.get(blk.get("tool_use_id"), {})
            tool = meta.get("name", "unknown")
            command = str((meta.get("input") or {}).get("command") or "")
            text = _text_of(blk.get("content"))
            failure_class, exit_code = _classify(tool, text)
            out.append({
                "ts": _iso_epoch(rec.get("timestamp")),
                "harness": "claude",
                "source": "claude_transcript",
                "repo": repo,
                "failure_class": failure_class,
                # schema_title is the v1 uniform "tool" analog; `tool` is the
                # harness-native alias issue #249 names. Both carry the tool name.
                "schema_title": tool,
                "tool": tool,
                "exit_code": exit_code,
                "attempt": 0,  # transcripts have no retry notion; fixed for v1 uniformity
                "stderr_excerpt": _excerpt(text),
                "detail": f"{tool} tool error ({failure_class})",
                "expected": _is_expected(tool, command, exit_code),
                "is_sidechain": bool(rec.get("isSidechain")),
                "session_id": rec.get("sessionId") or session_fallback,
                "record_uuid": rec.get("uuid"),
                "fingerprint": _fingerprint(failure_class, tool, text),
            })
    return out


# --- repo-slug resolution and watermark state ---

_SLUG_CACHE: dict[str, str] = {}


def _slug_for_cwd(cwd: str | None) -> str:
    """Slug (owner/name) of the git origin at a transcript's recorded `cwd`,
    cached per cwd; "unknown" when none resolves. Keys the per-repo buffer the
    same way the Goose drain keys it off the live origin."""
    key = cwd or ""
    if key in _SLUG_CACHE:
        return _SLUG_CACHE[key]
    slug = "unknown"
    if cwd and Path(cwd).is_dir():
        try:
            url = subprocess.run(["git", "-C", cwd, "remote", "get-url", "origin"],
                                 capture_output=True, text=True, timeout=10).stdout.strip()
            if url:
                u = url[:-4] if url.endswith(".git") else url
                u = u.split("://", 1)[-1].split("@", 1)[-1].replace(":", "/", 1)
                parts = [p for p in u.split("/") if p]
                if len(parts) >= 2:
                    slug = "/".join(parts[-2:])
        except (OSError, subprocess.SubprocessError):
            pass
    _SLUG_CACHE[key] = slug
    return slug


def _first_cwd(data: bytes) -> str | None:
    """The `cwd` of a transcript's first record - the working dir its tools ran
    in, used to resolve the repo slug for the whole file."""
    for raw in data.split(b"\n"):
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if rec.get("cwd"):
            return rec["cwd"]
    return None


def _load_watermarks(state_file: Path) -> dict:
    try:
        return json.loads(state_file.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_watermarks(state_file: Path, marks: dict) -> None:
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(marks, indent=2, sort_keys=True))
    except OSError:
        pass  # a failed watermark write just means the next sweep re-reads; harmless


def _append_records(records: list[dict], failure_dir: Path) -> int:
    """Append failure-records to their per-repo buffer. Best-effort: a write
    error must never break the drain (telemetry is not the hot path)."""
    written = 0
    try:
        failure_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    by_repo: dict[str, list[dict]] = {}
    for r in records:
        by_repo.setdefault(r["repo"], []).append(r)
    for repo, recs in by_repo.items():
        path = failure_dir / f"{repo.replace('/', '-')}.jsonl"
        try:
            with path.open("a", encoding="utf-8") as f:
                for r in recs:
                    f.write(json.dumps(r) + "\n")
                    written += 1
        except OSError:
            pass
    return written


# --- drain entrypoint ---

def drain(root: Path = PROJECTS_ROOT, *, session: str | None = None,
          repo: str | None = None, failure_dir: Path = FAILURE_DIR,
          state_file: Path = WATERMARK_FILE, dry_run: bool = False) -> dict:
    """Sweep transcripts under `root`, append new is_error records to the buffer,
    and advance each file's byte watermark. `session` narrows to one session's
    `*.jsonl`; `repo` overrides the per-cwd slug. Returns a summary dict."""
    if session:
        files = sorted(root.glob(f"**/{session}.jsonl"))
    else:
        files = sorted(root.glob("**/*.jsonl"))
    marks = _load_watermarks(state_file)
    all_records: list[dict] = []
    new_marks = dict(marks)
    scanned = 0
    for path in files:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        scanned += 1
        size = len(data)
        key = str(path)
        prev = marks.get(key, {})
        watermark = prev.get("offset", 0) if isinstance(prev, dict) else 0
        if size < watermark:  # file rotated/truncated under us -> re-read from 0
            watermark = 0
        slug = repo or _slug_for_cwd(_first_cwd(data))
        recs = _records_in_file(data, watermark, slug, path.stem)
        all_records.extend(recs)
        new_marks[key] = {"offset": size, "size": size}

    written = 0 if dry_run else _append_records(all_records, failure_dir)
    if not dry_run:
        _save_watermarks(state_file, new_marks)

    by_class: dict[str, int] = {}
    for r in all_records:
        by_class[r["failure_class"]] = by_class.get(r["failure_class"], 0) + 1
    genuine = sum(1 for r in all_records if not r["expected"])
    return {
        "files_scanned": scanned,
        "errors_found": len(all_records),
        "genuine": genuine,
        "expected": len(all_records) - genuine,
        "by_class": by_class,
        "written": written,
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Drain Claude Code transcript tool-use failures (is_error) "
                    "into the per-repo failure-record buffer.")
    ap.add_argument("--root", type=Path, default=PROJECTS_ROOT,
                    help="transcript root (default ~/.claude/projects)")
    ap.add_argument("--session", default=None,
                    help="drain only this session id's transcript (for a SessionEnd hook)")
    ap.add_argument("--repo", default=None,
                    help="override the per-cwd repo slug used to key the buffer")
    ap.add_argument("--state", type=Path, default=WATERMARK_FILE,
                    help="watermark state file (default in the buffer dir)")
    ap.add_argument("--failure-dir", type=Path, default=FAILURE_DIR,
                    help="buffer directory (default ~/.cache/agentic-os/tool-failures)")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report, but write nothing and do not advance the watermark")
    args = ap.parse_args(argv)

    summary = drain(args.root, session=args.session, repo=args.repo,
                    failure_dir=args.failure_dir, state_file=args.state,
                    dry_run=args.dry_run)

    cls = ", ".join(f"{k} {v}" for k, v in sorted(summary["by_class"].items()))
    print(f"claude-drain: {summary['files_scanned']} transcript(s) scanned, "
          f"{summary['errors_found']} new error(s) "
          f"({summary['genuine']} genuine / {summary['expected']} expected)"
          + (f" [{cls}]" if cls else ""), file=sys.stderr)
    print(f"claude-drain: {summary['written']} record(s) "
          f"{'would be written (dry-run)' if summary['dry_run'] else 'written to buffer'}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the check-only pre-commit hook set across every workspace git repo.

For each sibling coilysiren/* repo with a .pre-commit-config.yaml, write a
temporary copy of the config with the auto-applying (file-mutating) hooks
stripped out, run `pre-commit run --all-files --config <tmp>` against it, then
delete the temp file. Pointing pre-commit at a stripped config means no hook
ever rewrites a tracked file, so the sweep stays read-only without any
run-then-revert dance. Per-hook exclude: regexes still apply (no flag disables
them); --all-files is the "rerun over everything" lever.

Reports a per-repo Passed/Failed summary plus the failing hook ids.

Spans every git working tree under ~/projects/<org>/* via
agentic_os.config.iter_workspace_repos, not just the org dir the running
agentic-os checkout sits in. Override the root with $PROJECTS_ROOT.
See coilysiren/agentic-os-kai#560.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from agentic_os import config as cfg  # noqa: E402

TIMEOUT = 300

# Hooks that rewrite files in place. Stripped from the temp config so the
# sweep never mutates a tree. Extend as new fixers show up in consumer configs.
MUTATING_HOOK_IDS = {
    "trailing-whitespace",
    "end-of-file-fixer",
    "mixed-line-ending",
    "requirements-txt-fixer",
    "fix-byte-order-marker",
    "fix-encoding-pragma",
    "double-quote-string-fixer",
    "pretty-format-json",
    "sort-simple-yaml",
    "black",
    "blacken-docs",
    "isort",
    "ruff-format",
    "prettier",
    "gofmt",
    "goimports",
    "rustfmt",
    "cargo-fmt",
    "autopep8",
    "yapf",
}

RESULT_RE = re.compile(r"^(?P<name>.+?)\.{3,}(?P<status>Passed|Failed|Skipped)\s*$")
ID_RE = re.compile(r"-\s*id:\s*([A-Za-z0-9._-]+)")


def strip_mutating_hooks(text: str) -> tuple[str, list[str]]:
    """Drop every `- id: <mutating>` block from a pre-commit config text."""
    lines = text.split("\n")
    out: list[str] = []
    removed: list[str] = []
    skipping = False
    dash_indent = 0
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if skipping:
            if stripped == "":
                skipping = False
            elif indent > dash_indent:
                continue  # continuation line of the stripped hook
            else:
                skipping = False
        m = ID_RE.match(stripped)
        if m and m.group(1) in MUTATING_HOOK_IDS:
            removed.append(m.group(1))
            dash_indent = indent
            skipping = True
            continue
        out.append(line)
    return "\n".join(out), removed


def run_for_repo(repo: Path) -> dict:
    src = repo / ".pre-commit-config.yaml"
    stripped_text, removed = strip_mutating_hooks(src.read_text(encoding="utf-8"))
    tmp = repo / ".pre-commit-config.sweep-tmp.yaml"
    tmp.write_text(stripped_text, encoding="utf-8")
    try:
        proc = subprocess.run(
            ["pre-commit", "run", "--all-files", "--config", str(tmp),
             "--color", "never"],
            cwd=str(repo), capture_output=True, text=True, timeout=TIMEOUT,
        )
    except FileNotFoundError:
        return {"status": "error", "detail": "pre-commit not on PATH"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "detail": f"timeout after {TIMEOUT}s"}
    finally:
        tmp.unlink(missing_ok=True)

    text = proc.stdout + proc.stderr
    failed = [
        m.group("name").strip()
        for line in text.splitlines()
        if (m := RESULT_RE.match(line.strip())) and m.group("status") == "Failed"
    ]
    return {
        "status": "ok" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "failed_hooks": failed,
        "stripped": sorted(set(removed)),
        "raw_tail": "\n".join(text.splitlines()[-40:]) if proc.returncode else "",
    }


def main() -> int:
    all_repos = cfg.iter_workspace_repos()
    repos = [d for d in all_repos if (d / ".pre-commit-config.yaml").is_file()]
    no_config = sorted(
        d.name for d in all_repos
        if not (d / ".pre-commit-config.yaml").is_file()
    )

    results = {r.name: run_for_repo(r) for r in repos}

    passing = [n for n, r in results.items() if r["status"] == "ok"]
    failing = [(n, r) for n, r in results.items() if r["status"] == "fail"]
    errored = [(n, r) for n, r in results.items() if r["status"] == "error"]

    print("=" * 70)
    print(f"pre-commit sweep: {len(repos)} repos with a config "
          f"({len(no_config)} git repos have none)")
    print("mutating hooks stripped before each run; sweep is read-only")
    print("=" * 70)

    print(f"\nPASSING ({len(passing)}):")
    for n in passing:
        print(f"  OK   {n}")

    print(f"\nFAILING ({len(failing)}), fewest failed hooks first:")
    for n, r in sorted(failing, key=lambda x: len(x[1]["failed_hooks"])):
        hooks = ", ".join(r["failed_hooks"]) or "(nonzero exit, no parsed hook)"
        print(f"  FAIL {n}  [{hooks}]")

    if errored:
        print(f"\nERRORED ({len(errored)}):")
        for n, r in errored:
            print(f"  ERR  {n}: {r['detail']}")

    if no_config:
        print(f"\nNO PRE-COMMIT CONFIG ({len(no_config)}):")
        print("  " + ", ".join(no_config))

    print("\n" + "=" * 70)
    print("DETAIL (failing repos, fewest failed hooks first)")
    print("=" * 70)
    for n, r in sorted(failing, key=lambda x: len(x[1]["failed_hooks"])):
        print(f"\n### {n}  (rc={r['returncode']}, {len(r['failed_hooks'])} failed hooks)")
        print("  --- tail of output ---")
        for line in r["raw_tail"].splitlines():
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

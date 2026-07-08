#!/usr/bin/env python3
"""Assert every catalog repo's .pre-commit-config.yaml references the
expected coilysiren/agentic-os hook IDs.

Walks every git working tree under ~/projects/<org>/* via
agentic_os.config.iter_workspace_repos (or `--source github` to query the
contents API), reads each repo's `.pre-commit-config.yaml`, and reports
which expected hook IDs are missing. Override the local root with
$PROJECTS_ROOT. See coilysiren/agentic-os-kai#560.

The expected set is the hook IDs declared in this repo's
`.pre-commit-hooks.yaml`, excluding hooks that are manual-only opt-ins. Run
this after a `apply-agentic-os-hooks.py` sweep to verify every consumer landed
the managed block.

Usage:
    python3 scripts/audit-pre-commit-coverage.py            # local fleet
    python3 scripts/audit-pre-commit-coverage.py --source github
    python3 scripts/audit-pre-commit-coverage.py --skip X Y

Stdlib + PyYAML. Shells out to `gh` for the repo list (and contents in
github mode).

Exit code: 0 if every checked-out repo has full coverage, 1 otherwise.
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    import yaml
except ModuleNotFoundError:
    sys.stderr.write(
        "audit-pre-commit-coverage: PyYAML required. pip install pyyaml\n"
    )
    sys.exit(2)

from agentic_os import config as cfg  # noqa: E402

HOOKS_FILE = REPO_ROOT / ".pre-commit-hooks.yaml"
OWNER = "coilysiren"
AGENTIC_OS_URL = "https://github.com/coilysiren/agentic-os"


def expected_hook_ids() -> list[str]:
    data = yaml.safe_load(HOOKS_FILE.read_text())
    out = []
    for hook in data:
        stages = set(hook.get("stages") or [])
        if stages and stages <= {"manual"}:
            continue
        out.append(hook["id"])
    return out


def gh(*args: str) -> str:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)!r} failed (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def list_active_repos() -> list[str]:
    out = gh(
        "repo", "list", OWNER,
        "--limit", "200",
        "--no-archived",
        "--source",
        "--json", "name",
        "--jq", ".[].name",
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def read_local_config(repo_dir: Path) -> str | None:
    path = repo_dir / ".pre-commit-config.yaml"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def read_remote_config(repo: str) -> str | None:
    try:
        payload_raw = gh(
            "api", f"repos/{OWNER}/{repo}/contents/.pre-commit-config.yaml"
        )
    except RuntimeError as exc:
        if "404" in str(exc) or "Not Found" in str(exc):
            return None
        raise
    payload: dict[str, Any] = json.loads(payload_raw)
    if payload.get("type") != "file":
        return None
    encoded = payload.get("content", "").replace("\n", "")
    if not encoded:
        return ""
    try:
        return base64.b64decode(encoded).decode("utf-8")
    except UnicodeDecodeError:
        return None


def _is_agentic_os_repo(repo_url: str) -> bool:
    """Match the agentic-os upstream-ref entry regardless of host or owner.

    The managed block points at the Forgejo mirror
    (forgejo.coilysiren.me/coilyco-flight-deck/agentic-os) while the GitHub
    mirror uses github.com/coilysiren/agentic-os. Match on the trailing
    `/agentic-os` path component so either lands.
    """
    return repo_url.rstrip("/").endswith("/agentic-os")


def referenced_hook_ids(config_text: str) -> set[str]:
    """Pull hook IDs from the agentic-os upstream-ref block(s)."""
    try:
        data = yaml.safe_load(config_text)
    except yaml.YAMLError:
        return set()
    out: set[str] = set()
    for entry in (data or {}).get("repos") or []:
        if not isinstance(entry, dict):
            continue
        repo = entry.get("repo", "")
        if not _is_agentic_os_repo(repo):
            continue
        for hook in entry.get("hooks") or []:
            if isinstance(hook, dict) and "id" in hook:
                out.add(hook["id"])
    return out


def audit_config(
    repo: str, config_text: str | None, expected: list[str]
) -> dict[str, Any]:
    if config_text is None:
        return {"repo": repo, "status": "no-config", "missing": expected}
    referenced = referenced_hook_ids(config_text)
    missing = [h for h in expected if h not in referenced]
    if not missing:
        return {"repo": repo, "status": "ok", "missing": []}
    return {"repo": repo, "status": "missing", "missing": missing}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument(
        "--source", choices=["local", "github"], default="local",
        help="local: walk ~/projects/<org>/* on disk (default). github: query the contents API."
    )
    ap.add_argument("--repo", help="audit a single repo by name")
    ap.add_argument("--skip", nargs="*", default=[])
    args = ap.parse_args(argv)

    expected = expected_hook_ids()
    skip = set(args.skip)

    # Local mode drives off the on-disk checkout set so it spans every org dir.
    # Github mode keeps querying the coilysiren owner via the contents API.
    results = []
    if args.source == "local":
        dirs = cfg.iter_workspace_repos()
        if args.repo:
            dirs = [d for d in dirs if d.name == args.repo]
        else:
            dirs = [d for d in dirs if d.name not in skip]
        print(
            f"Auditing {len(dirs)} repo(s) against {len(expected)} expected "
            f"hook(s) from {AGENTIC_OS_URL}/.pre-commit-hooks.yaml"
        )
        print(f"Source: {args.source}")
        print()
        for d in dirs:
            results.append(audit_config(d.name, read_local_config(d), expected))
    else:
        names = [args.repo] if args.repo else [
            r for r in list_active_repos() if r not in skip
        ]
        print(
            f"Auditing {len(names)} repo(s) against {len(expected)} expected "
            f"hook(s) from {AGENTIC_OS_URL}/.pre-commit-hooks.yaml"
        )
        print(f"Source: {args.source}")
        print()
        for name in names:
            try:
                results.append(
                    audit_config(name, read_remote_config(name), expected)
                )
            except RuntimeError as exc:
                results.append(
                    {"repo": name, "status": "error", "missing": [], "error": str(exc)}
                )

    by_status: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    for status in ("ok", "missing", "no-config", "error"):
        entries = by_status.get(status, [])
        if not entries:
            continue
        print(f"== {status} ({len(entries)}) ==")
        for r in entries:
            if r["missing"]:
                print(f"  {r['repo']:28} missing: {', '.join(r['missing'])}")
            elif r.get("error"):
                print(f"  {r['repo']:28} error: {r['error']}")
            else:
                print(f"  {r['repo']:28}")
        print()

    bad = (
        len(by_status.get("missing", []))
        + len(by_status.get("no-config", []))
        + len(by_status.get("error", []))
    )
    if bad:
        print(f"Coverage incomplete: {bad} repo(s) need attention.")
        return 1
    print("Coverage complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

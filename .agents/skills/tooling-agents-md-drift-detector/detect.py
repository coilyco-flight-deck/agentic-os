#!/usr/bin/env python3
"""Cross-repo AGENTS.md drift detector. See SKILL.md.

Classifies each repo's AGENTS.md against a canonical AGENTS.md:

- linked-canonical: symlink to canonical (no drift possible).
- linked-other:     symlink to something else.
- delegating:       regular file with an explicit delegation header pointing
                    at canonical. This is the intended layering pattern; not
                    drift.
- forked:           regular file without delegation header, especially when
                    it re-states canonical section headers. This is the
                    failure mode the skill catches.
- missing:          no AGENTS.md.

Output: a markdown report. By default goes to the configured inbox if reachable,
otherwise stdout. Override with `--out <path>` or `AGENTS_DRIFT_INBOX` env.

Configurable via env vars:
- AGENTS_DRIFT_REPOS_PARENT: directory holding sibling repos to scan.
- AGENTS_DRIFT_CANONICAL: path to canonical AGENTS.md.
- AGENTS_DRIFT_INBOX: directory to write the report into.

Exits non-zero if any `forked` entries exist (CI-friendly).
"""
import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

REPOS_PARENT = Path(os.environ.get("AGENTS_DRIFT_REPOS_PARENT", Path.home() / "projects"))
CANONICAL = Path(os.environ.get("AGENTS_DRIFT_CANONICAL", REPOS_PARENT / "AGENTS.md"))
DEFAULT_INBOX = Path(os.environ.get("AGENTS_DRIFT_INBOX_DEFAULT", REPOS_PARENT / "inbox"))

DELEGATION_PATTERNS = (
    re.compile(r"See\s+`?\.\./AGENTS\.md`?", re.IGNORECASE),
    re.compile(
        r"(load|loaded)\s+globally\s+via.*AGENTS\.md",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"CLAUDE\.md.*AGENTS\.md", re.DOTALL),
    re.compile(
        r"(operating context|canonical context|full context).*AGENTS\.md",
        re.IGNORECASE | re.DOTALL,
    ),
)

# Section headers that appear in every per-repo AGENTS.md by design.
# Overlap on these is not a forking signal.
STANDARDIZED_SECTIONS = frozenset({
    "## Commands",
    "## See also",
})


def has_delegation_header(text: str) -> bool:
    # Scan a wider window than 800 chars - some repos put the delegation
    # pointer near the end (e.g. homebrew-tap "Canonical context" section).
    return any(p.search(text) for p in DELEGATION_PATTERNS)


def canonical_section_headers(canonical_text: str) -> set[str]:
    return {
        line.strip()
        for line in canonical_text.splitlines()
        if line.startswith("## ")
    }


def categorize(repo: Path, canonical_text: str, canonical_headers: set[str]):
    am = repo / "AGENTS.md"
    if not am.exists() and not am.is_symlink():
        return ("missing", None)
    if am.is_symlink():
        target = os.readlink(am)
        # Resolve symlink target relative to the repo and compare to canonical.
        resolved = (am.parent / target).resolve()
        if resolved == CANONICAL.resolve():
            return ("linked-canonical", target)
        return ("linked-other", target)
    text = am.read_text(errors="ignore")
    if has_delegation_header(text):
        return ("delegating", None)
    # No delegation header. Check whether canonical section headers are
    # restated (a sign of forking rather than a legitimately standalone
    # project-only AGENTS.md).
    repo_headers = {
        line.strip()
        for line in text.splitlines()
        if line.startswith("## ")
    }
    overlap = (repo_headers & canonical_headers) - STANDARDIZED_SECTIONS
    if overlap:
        return ("forked", f"restates {len(overlap)} canonical sections: {', '.join(sorted(overlap))[:120]}")
    # Standalone project-only file. Not drift.
    return ("standalone", None)


def resolve_output(arg_out: str | None) -> Path | None:
    if arg_out:
        return Path(arg_out).expanduser()
    env = os.environ.get("AGENTS_DRIFT_INBOX")
    if env:
        return Path(env).expanduser()
    if DEFAULT_INBOX.parent.exists():
        return DEFAULT_INBOX
    return None  # stdout fallback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="output directory for the report")
    args = parser.parse_args()

    if not CANONICAL.exists():
        print(f"canonical not found: {CANONICAL}", file=sys.stderr)
        return 2
    canonical_text = CANONICAL.read_text()
    canonical_headers = canonical_section_headers(canonical_text)

    buckets: dict[str, list[tuple[str, str | None]]] = {
        "forked": [],
        "linked-other": [],
        "missing": [],
        "delegating": [],
        "standalone": [],
        "linked-canonical": [],
    }
    for repo in sorted(REPOS_PARENT.iterdir()):
        if not repo.is_dir() or not (repo / ".git").exists():
            continue
        # Skip the canonical repo itself.
        if (repo / "AGENTS.md").resolve() == CANONICAL.resolve():
            continue
        status, detail = categorize(repo, canonical_text, canonical_headers)
        buckets[status].append((repo.name, detail))

    today = date.today().isoformat()
    lines = [f"# {today} AGENTS.md drift report", "", f"Canonical: `{CANONICAL}`", ""]
    for label in ("forked", "linked-other", "missing", "delegating",
                  "standalone", "linked-canonical"):
        items = buckets[label]
        lines.append(f"## {label} ({len(items)})")
        lines.append("")
        for name, detail in items:
            lines.append(f"- {name}" + (f" - {detail}" if detail else ""))
        lines.append("")
    body = "\n".join(lines)

    out_dir = resolve_output(args.out)
    if out_dir is None:
        sys.stdout.write(body)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{today}-agents-md-drift.md"
        out_file.write_text(body)
        print(f"wrote {out_file}")

    return 1 if buckets["forked"] else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Enforce the catalog-trifecta cross-link convention.

Every catalog repo carries three audience-distinct entry-point markdown
files at the root plus the ward command spec. Each markdown file
cross-links to the other two plus to the YAML. This makes the entry
point reachable from any one of them with a single click.

The four files:
    README.md           - pitch + quick start for human readers
    AGENTS.md           - per-repo agent operating rules
    docs/FEATURES.md    - flat inventory of what ships today
    .ward/ward.yaml   - allowlisted dev commands

This validator checks, per markdown file:
    1. The file exists.
    2. The file contains a "## See also" section header.
    3. The file contains markdown links resolving to each of the other
       three canonical paths (the two peer .md files plus .ward/ward.yaml).
    4. AGENTS.md contains the standard repo-local agent heading set.

The .ward/ward.yaml file only needs to exist; no back-link required,
since YAML is machine-consumed and the prose home is the .md files.

Usage (when run directly):
    python3 scripts/check-catalog-trifecta.py

Exits 0 on clean, 1 on any violation with a per-file report on stderr.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from agentic_os.config import is_enabled

REPO_ROOT = Path.cwd()
HOOK_ID = "catalog-trifecta"

# Markdown files where the See also section lives.
MD_FILES = [
    Path("README.md"),
    Path("AGENTS.md"),
    Path("docs/FEATURES.md"),
]

# Existence-only fourth member: the ward command spec.
CATALOG_YAMLS = (Path(".ward/ward.yaml"),)

SEE_ALSO_HEADER = re.compile(r"^##\s+See also\s*$", re.MULTILINE)

AGENTS_REQUIRED_H2 = [
    "Scope",
    "Project shape",
    "Repo boundaries",
    "Commands",
    "Validation",
    "Safety",
    "Cross-repo contracts",
    "Release",
    "Agent rules",
    "See also",
]

# Markdown inline link target extraction. Mirrors the form used by
# check-dead-links.py so the two validators agree on what a "link" is.
LINK_RE = re.compile(
    r"(?<!\!)\[(?P<text>[^\]\n]+)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)

def link_targets(text: str) -> set[str]:
    """Resolved-target paths for every inline markdown link in `text`.

    Strips anchor fragments. Returns relative paths as-is (no resolution
    against any base dir); resolution happens in the caller.
    """
    out: set[str] = set()
    for m in LINK_RE.finditer(text):
        target = m.group("target").split("#", 1)[0].strip()
        if target:
            out.add(target)
    return out


def file_links_to(source_path: Path, target_path: Path, body: str) -> bool:
    """True if body contains a markdown link whose resolved target equals
    target_path (relative to repo root)."""
    targets = link_targets(body)
    source_dir = (REPO_ROOT / source_path).parent
    for t in targets:
        candidate = (source_dir / t).resolve()
        try:
            rel = candidate.relative_to(REPO_ROOT.resolve())
        except ValueError:
            continue
        if rel == target_path:
            return True
    return False


def resolve_catalog_yaml() -> Path | None:
    """Return whichever catalog yaml this repo carries, if any."""
    for candidate in CATALOG_YAMLS:
        if (REPO_ROOT / candidate).is_file():
            return candidate
    return None


def check_md_file(md_path: Path, catalog_yaml: Path) -> list[str]:
    violations: list[str] = []
    abs_path = REPO_ROOT / md_path

    if not abs_path.is_file():
        violations.append(f"{md_path}: missing. Trifecta requires this file at the canonical path.")
        return violations

    body = abs_path.read_text(encoding="utf-8", errors="replace")

    if not SEE_ALSO_HEADER.search(body):
        violations.append(f"{md_path}: missing '## See also' section header.")

    peers = [p for p in MD_FILES if p != md_path] + [catalog_yaml]
    for peer in peers:
        if not file_links_to(md_path, peer, body):
            violations.append(
                f"{md_path}: no markdown link resolves to {peer}. "
                f"The 'See also' section must point at the other three "
                f"catalog-trifecta files."
            )

    if md_path == Path("AGENTS.md"):
        violations.extend(check_agents_headings(body))

    return violations


def markdown_h2s(body: str) -> set[str]:
    headings: set[str] = set()
    in_code = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith("## ") and not stripped.startswith("### "):
            headings.add(re.sub(r"\s+", " ", stripped[3:].strip()))
    return headings


def check_agents_headings(body: str) -> list[str]:
    headings = markdown_h2s(body)
    missing = [h for h in AGENTS_REQUIRED_H2 if h not in headings]
    if not missing:
        return []
    return [
        "AGENTS.md: missing required H2 heading(s): "
        + ", ".join(f"## {h}" for h in missing)
        + ". Standard sections keep repo-local operating rules scannable."
    ]


def check_catalog_yaml(catalog_yaml: Path | None) -> list[str]:
    if catalog_yaml is None:
        return ["catalog yaml missing. Every catalog repo needs .ward/ward.yaml."]
    return []


def main() -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    catalog_yaml = resolve_catalog_yaml()
    all_violations: list[str] = []
    # Fall back to .ward/ward.yaml so error messages always name a concrete file.
    link_target = catalog_yaml or CATALOG_YAMLS[0]
    for md in MD_FILES:
        all_violations.extend(check_md_file(md, link_target))
    all_violations.extend(check_catalog_yaml(catalog_yaml))

    if not all_violations:
        print("catalog-trifecta check: OK")
        return 0

    for v in all_violations:
        sys.stderr.write(f"FAIL: {v}\n")
    sys.stderr.write(f"\n{len(all_violations)} catalog-trifecta violation(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

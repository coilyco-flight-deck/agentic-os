#!/usr/bin/env python3
"""
Find dead cross-links anywhere in the repo.

Scans every Markdown file in the repo (root README/AGENTS, docs/, co-located
module READMEs, the skill tree, etc.), extracts inline markdown links
(`[text](target)` and `[text](target#anchor)`), and reports any local-relative
target that doesn't resolve to a real file or directory. A link that resolves
**outside the repo root** is a hard violation, not a skip - an internal `../`
link is validated for existence like any other, while one that escapes the repo
fails.

Out of scope:
- External URLs (anything with a scheme, e.g. http://, mailto:).
- Bare anchors (`#section`) - no anchor index is maintained.
- Reference-style links (`[text][ref]` definitions).
- Image links (`![alt](src)`).
- Bare skill-name mentions in prose.

Directory skipping mirrors documentation-layout (`SKIP_DIR_NAMES`: `.git`,
`node_modules`, build outputs, caches), plus per-repo `excludes` from
`[tool.agentic-os.dead-cross-links]`.

Usage (when run directly):
    python3 scripts/check-dead-links.py            # scan the whole repo
    python3 scripts/check-dead-links.py path ...   # scan only the given files

Canonical copy lives in coilyco-flight-deck/agentic-os/scripts/. Each consumer repo
gets a stamped copy via agentic-os-kai's apply-skill-discipline-hooks
rollout. Exits 0 on clean, 1 with per-violation report on stderr.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from agentic_os.pre_commit.tree import should_skip
from agentic_os.config import (
    is_build_output,
    is_enabled,
    is_excluded,
    load_excludes,
)

HOOK_ID = "dead-cross-links"

# Pre-commit runs the hook with the consumer repo as cwd.
REPO_ROOT = Path.cwd()

LINK_RE = re.compile(
    r"(?<!\!)\[(?P<text>[^\]\n]+)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)

EXTERNAL_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "ftp://",
    "git@",
    "tel:",
    "javascript:",
)

# Directory names never worth walking. Mirrors documentation-layout so the two
SKIP_FILE_BASENAMES = {"TEMPLATE.md"}
PLACEHOLDER_TARGETS = {"...", "TBD", "TODO"}


def is_external(target: str) -> bool:
    if target.startswith("#"):
        return True
    if target.startswith(EXTERNAL_PREFIXES):
        return True
    if target in PLACEHOLDER_TARGETS:
        return True
    if "://" in target.split("/")[0]:
        return True
    # A `../` link is NOT external. It is resolved and validated like any other
    # internal link; if it escapes the repo root, check_file() flags it.
    return False


def strip_anchor(target: str) -> str:
    return target.split("#", 1)[0]


def _rel_or_none(path: Path) -> Path | None:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return None


def iter_markdown_files(roots: list[Path]):
    excludes = load_excludes(HOOK_ID)

    def keep(path: Path) -> bool:
        if path.name in SKIP_FILE_BASENAMES:
            return False
        rel = _rel_or_none(path)
        if rel is None:
            return True
        if should_skip(rel) or is_excluded(rel, excludes):
            return False
        # A baked bundle's relative links resolve in the catalogue it came from,
        # never in the bundle, and it is not this repo's content either way.
        return not is_build_output(rel, REPO_ROOT)

    for root in roots:
        if root.is_file() and root.suffix == ".md":
            if keep(root):
                yield root
            continue
        if root.is_dir():
            for p in sorted(root.rglob("*.md")):
                if keep(p):
                    yield p


def strip_fenced_code(text: str) -> str:
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("\n")
            continue
        out.append("\n" if in_fence else line)
    return "".join(out)


INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def strip_inline_code(text: str) -> str:
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)


def check_file(md_path: Path) -> list[str]:
    violations = []
    raw = md_path.read_text(errors="replace")
    text = strip_inline_code(strip_fenced_code(raw))
    rel_src = _rel_or_none(md_path) or md_path
    for m in LINK_RE.finditer(text):
        target_raw = m.group("target")
        if is_external(target_raw):
            continue
        target = strip_anchor(target_raw).strip()
        if not target:
            continue
        line_no = text.count("\n", 0, m.start()) + 1
        resolved = (md_path.parent / target).resolve()
        rel_resolved = _rel_or_none(resolved)
        if rel_resolved is None:
            violations.append(
                f"{rel_src}:{line_no}: repo-escaping link "
                f"[{m.group('text')}]({target_raw}) -> resolves outside "
                f"repo: {resolved}"
            )
            continue
        if not resolved.exists():
            violations.append(
                f"{rel_src}:{line_no}: dead link "
                f"[{m.group('text')}]({target_raw}) -> {rel_resolved}"
            )
    return violations


def main(argv: list[str] | None = None) -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        prog="check-dead-links",
        description="Find dead cross-links anywhere in the repo.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional list of paths to scope the dead-link check to. "
        "When empty, the entire repo is walked.",
    )
    ns = parser.parse_args(argv[1:])

    if ns.paths:
        roots = [Path(a).resolve() for a in ns.paths]
    else:
        roots = [REPO_ROOT]

    all_violations: list[str] = []
    for md in iter_markdown_files(roots):
        all_violations.extend(check_file(md))

    if not all_violations:
        print("dead-link check: OK")
        return 0

    for v in all_violations:
        sys.stderr.write(f"FAIL: {v}\n")
    sys.stderr.write(f"\n{len(all_violations)} dead link(s).\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

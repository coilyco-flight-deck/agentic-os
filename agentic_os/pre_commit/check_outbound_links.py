#!/usr/bin/env python3
"""
Outbound link hygiene, offline.

`dead-cross-links` validates repo-relative targets and returns early on
anything carrying a scheme, so every outbound link in the estate was unchecked.
This hook takes the other half: links that leave the repository. It stays
offline because pre-commit must not depend on the network, so it does static
analysis only and never fetches. Liveness is `agentic_os/link_liveness.py`,
a scheduled job rather than a commit hook.

Four checks, all driven by `agentic_os/outbound_link_rules.json`:

1. Retired names and paths. A rename edits the table, not this file.
2. Canonical host per link class, when the repo declares one.
3. Link text that names one project while the target names another.
4. Placeholder and local URLs.

Use versus mention. Fenced code and inline code are stripped before the name
scan, so a doc narrating a rename writes the retired name in backticks and a
doc still *using* it does not. That is the whole exemption mechanism for
checks 1 and 4, and it is why paths that legitimately keep a pre-rename spelling
(SSM parameters, IAM ARNs) pass without an allowlist.

Scope: Markdown and HTML. Per-repo `excludes` and `canonical_repo_host` live
under `[tool.agentic-os.outbound-link-hygiene]`. Exits 0 clean, 1 with a
per-violation report on stderr.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, NamedTuple
from urllib.parse import urlsplit

from agentic_os.config import (
    get_str_option,
    is_build_output,
    is_enabled,
    is_excluded,
    load_excludes,
)
from agentic_os.pre_commit.check_dead_links import (
    strip_fenced_code,
    strip_inline_code,
)
from agentic_os.pre_commit.tree import should_skip

HOOK_ID = "outbound-link-hygiene"
REPO_ROOT = Path.cwd()
RULES_PATH = Path(__file__).resolve().parent.parent / "outbound_link_rules.json"

SCANNED_SUFFIXES = {".md", ".markdown", ".html", ".htm"}
SKIP_FILE_BASENAMES = {"TEMPLATE.md"}

HTML_LINK_RE = re.compile(
    r"<a\b[^>]*?\bhref\s*=\s*[\"'](?P<target>[^\"']*)[\"'][^>]*>(?P<text>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
MD_LINK_RE = re.compile(
    r"(?<!\!)\[(?P<text>[^\]\n]*)\]\((?P<target>[^)\s]*)(?:\s+\"[^\"]*\")?\)"
)
AUTOLINK_RE = re.compile(r"<(?P<target>(?:https?|mailto):[^>\s]+)>")
BARE_URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
TAG_RE = re.compile(r"<[^>]+>")
TRAILING_PUNCT = ".,;:!?)"


class Reference(NamedTuple):
    """One outbound reference: where it sits, where it points, what it says."""

    line: int
    url: str
    text: str | None


class NameRule(NamedTuple):
    matcher: re.Pattern[str]
    name: str
    replacement: str
    kind: str


def load_rules(path: Path | None = None) -> dict:
    return json.loads((path or RULES_PATH).read_text(encoding="utf-8"))


def build_name_rules(rules: dict) -> list[NameRule]:
    out: list[NameRule] = []
    for entry in rules.get("retired_names", []):
        name = entry["name"]
        body = r"\s+".join(re.escape(part) for part in name.split())
        flags = 0 if entry.get("case_sensitive") else re.IGNORECASE
        matcher = re.compile(
            r"(?<![A-Za-z0-9_-])" + body + r"(?![A-Za-z0-9_-])", flags
        )
        out.append(
            NameRule(matcher, name, entry["replacement"], entry.get("kind", "name"))
        )
    return out


def _blank(text: str, start: int, end: int) -> str:
    span = "".join("\n" if c == "\n" else " " for c in text[start:end])
    return text[:start] + span + text[end:]


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _clean_text(raw: str) -> str:
    return TAG_RE.sub("", raw).replace("`", "").replace("*", "").replace("_", "").strip()


def extract_references(text: str) -> list[Reference]:
    """Every outbound reference in a fence-stripped document.

    Each form is blanked once consumed so a URL inside a markdown link is not
    also counted as a bare URL, while line numbers survive the blanking.
    """
    refs: list[Reference] = []
    for matcher, has_text in (
        (HTML_LINK_RE, True),
        (MD_LINK_RE, True),
        (AUTOLINK_RE, False),
    ):
        while True:
            match = matcher.search(text)
            if match is None:
                break
            label = _clean_text(match.group("text")) if has_text else None
            refs.append(
                Reference(_line_of(text, match.start()), match.group("target"), label)
            )
            text = _blank(text, match.start(), match.end())
    for match in BARE_URL_RE.finditer(text):
        refs.append(
            Reference(_line_of(text, match.start()), match.group(0).rstrip(TRAILING_PUNCT), None)
        )
    return sorted(refs)


def _host(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def repo_slug(url: str, rules: dict) -> tuple[str, str, str, bool] | None:
    """Split an estate repository URL into host, org, repo, and is-bare-root."""
    host = _host(url)
    if host not in set(rules.get("estate_hosts", [])):
        return None
    try:
        parts = [p for p in urlsplit(url).path.split("/") if p]
    except ValueError:
        return None
    if len(parts) < 2 or parts[0] not in set(rules.get("estate_orgs", [])):
        return None
    repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    return host, parts[0], repo, len(parts) == 2


def line_violations(
    rel: str, text: str, name_rules: list[NameRule], rules: dict
) -> list[str]:
    """Checks 1 and 4 over prose: retired names, retired paths, local hosts.

    Runs on text with fences and inline code already removed, so a backticked
    mention of a retired name or an example `http://localhost` is exempt.
    """
    placeholder_hosts = set(rules.get("placeholder_hosts", []))
    out: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule in name_rules:
            if rule.matcher.search(line):
                out.append(
                    f"{rel}:{line_no}: retired-name - {rule.kind} '{rule.name}' is "
                    f"retired, use '{rule.replacement}' (backtick it to mention it)"
                )
        lowered = line.lower()
        for entry in rules.get("retired_paths", []):
            if entry["path"].lower() in lowered:
                out.append(
                    f"{rel}:{line_no}: retired-path - '{entry['path']}' does not "
                    f"resolve, use {entry['replacement']}"
                )
        for match in BARE_URL_RE.finditer(line):
            host = _host(match.group(0))
            if host in placeholder_hosts:
                out.append(
                    f"{rel}:{line_no}: placeholder-url - '{host}' is a local or "
                    f"example host, not something a reader can follow"
                )
    return out


def reference_violations(
    rel: str,
    refs: Iterable[Reference],
    rules: dict,
    canonical_host: str,
    known_slugs: set[str],
) -> list[str]:
    """Checks 2, 3 and 4 over extracted links."""
    placeholders = set(rules.get("placeholder_targets", []))
    out: list[str] = []
    for ref in refs:
        target = ref.url.strip()
        if ref.text is not None and target.lower() in placeholders:
            shown = target or "(empty)"
            out.append(
                f"{rel}:{ref.line}: placeholder-target - [{ref.text}]({shown}) "
                f"points nowhere"
            )
            continue
        parsed = repo_slug(target, rules)
        if parsed is None:
            continue
        host, org, repo, bare_root = parsed
        if canonical_host and host != canonical_host:
            out.append(
                f"{rel}:{ref.line}: canonical-host - {org}/{repo} is linked via "
                f"{host}, this repo declares {canonical_host}"
            )
        if ref.text and bare_root:
            label = ref.text.rsplit("/", 1)[-1]
            if label in known_slugs and label != repo:
                out.append(
                    f"{rel}:{ref.line}: text-target-mismatch - link text names "
                    f"'{label}' but the target is {org}/{repo}"
                )
    return out


def iter_files(roots: list[Path], excludes: list[str]) -> Iterable[Path]:
    def keep(path: Path) -> bool:
        if path.name in SKIP_FILE_BASENAMES or path.suffix.lower() not in SCANNED_SUFFIXES:
            return False
        try:
            rel = path.relative_to(REPO_ROOT)
        except ValueError:
            return True
        if should_skip(rel) or is_excluded(rel, excludes):
            return False
        return not is_build_output(rel, REPO_ROOT)

    for root in roots:
        if root.is_file():
            if keep(root):
                yield root
            continue
        if root.is_dir():
            for path in sorted(root.rglob("*")):
                if path.is_file() and keep(path):
                    yield path


def check_tree(roots: list[Path], rules: dict, canonical_host: str, excludes: list[str]) -> list[str]:
    name_rules = build_name_rules(rules)
    retired = {entry["name"] for entry in rules.get("retired_names", [])}
    documents: list[tuple[str, str, list[Reference]]] = []
    known_slugs: set[str] = set(retired)
    for path in iter_files(roots, excludes):
        try:
            rel = str(path.relative_to(REPO_ROOT))
        except ValueError:
            rel = str(path)
        raw = path.read_text(errors="replace")
        refs = extract_references(strip_fenced_code(raw))
        for ref in refs:
            parsed = repo_slug(ref.url.strip(), rules)
            if parsed is not None and parsed[3]:
                known_slugs.add(parsed[2])
        documents.append((rel, raw, refs))

    violations: list[str] = []
    for rel, raw, refs in documents:
        prose = strip_inline_code(strip_fenced_code(raw))
        violations.extend(line_violations(rel, prose, name_rules, rules))
        violations.extend(
            reference_violations(rel, refs, rules, canonical_host, known_slugs)
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    if not is_enabled(HOOK_ID):
        print(f"{HOOK_ID}: disabled by repo config")
        return 0
    parser = argparse.ArgumentParser(
        prog="check-outbound-links",
        description="Offline hygiene for links that leave the repository.",
    )
    parser.add_argument("paths", nargs="*", help="Optional paths to scope the scan to.")
    ns = parser.parse_args((sys.argv if argv is None else argv)[1:])

    roots = [Path(p).resolve() for p in ns.paths] if ns.paths else [REPO_ROOT]
    violations = check_tree(
        roots,
        load_rules(),
        get_str_option(HOOK_ID, "canonical_repo_host", ""),
        load_excludes(HOOK_ID),
    )
    if not violations:
        print(f"{HOOK_ID} check: OK")
        return 0
    for violation in violations:
        sys.stderr.write(f"FAIL: {violation}\n")
    sys.stderr.write(
        f"\n{len(violations)} outbound link violation(s). "
        f"Rules live in {RULES_PATH.name}, so a rename edits the table.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

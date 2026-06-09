#!/usr/bin/env python3
"""Canonicalize YAML to a maximum-strictness, deterministic form and autofix.

The strict canonical subset:

    * every mapping's keys are alpha-sorted, recursively
    * every sequence is sorted by the canonical serialization of its items,
      recursively (a sequence of mappings sorts by each item's normalized
      YAML text - a deterministic key that needs no per-list config)
    * no duplicate mapping keys (PyYAML silently keeps the last; we reject)
    * no anchors (&a), aliases (*a), or non-standard tags (!foo) - they make
      a file's meaning non-local and defeat line-wise diffing
    * no comments at all - a comment carries zero data, so stripping it is a
      safe autofix (the parser sees the same tree) and it retires the only
      case where canonicalization could relocate text. Dial off with
      no_comments = false to keep them.
    * canonical formatting: 2-space block indent, explicit `---` start, a
      single trailing newline, no tabs, no trailing whitespace

The hook autofixes in place (sorts, strips comments, reformats) and exits
non-zero when it changed anything, like ruff / black / end-of-file-fixer:
re-stage and commit.

Two conditions are reported but NOT auto-fixed, because a safe rewrite is
ambiguous: duplicate keys (which value wins?) and anchors/aliases/tags (inline
or keep the reference?). Those fail the hook for a human to resolve.

Usage:
    check-yaml-strict path/to/file.yaml [more...]   # pre-commit passes these
    check-yaml-strict                                # no args: walk the repo

Per-repo opt-outs live under [tool.agentic-os.yaml-strict] excludes = [...].
Origin: maximum-strictness YAML canonicalizer (Kai request).
"""

from __future__ import annotations

import io
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import YAMLError

from agentic_os.config import (
    get_bool_option,
    is_excluded,
    load_excludes,
    load_str_list,
)

HOOK_ID = "yaml-strict"
YAML_SUFFIXES = (".yaml", ".yml")
SKIP_DIR_NAMES = {".git", "node_modules", ".venv", "__pycache__", ".mypy_cache"}
REPO_ROOT = Path.cwd()


@dataclass(frozen=True)
class Options:
    """Resolved [tool.agentic-os.yaml-strict] strictness dials."""

    sort_keys: bool = True
    sort_sequences: bool = True
    explicit_start: bool = True
    no_anchors: bool = True
    no_comments: bool = True
    order_significant: tuple[str, ...] = ()


def _load_options() -> Options:
    return Options(
        sort_keys=get_bool_option(HOOK_ID, "sort_keys", True),
        sort_sequences=get_bool_option(HOOK_ID, "sort_sequences", True),
        explicit_start=get_bool_option(HOOK_ID, "explicit_start", True),
        no_anchors=get_bool_option(HOOK_ID, "no_anchors", True),
        no_comments=get_bool_option(HOOK_ID, "no_comments", True),
        order_significant=tuple(load_str_list(HOOK_ID, "order_significant")),
    )


def _yaml(explicit_start: bool = True) -> YAML:
    """A round-trip YAML configured for the canonical output form."""
    y = YAML()
    y.preserve_quotes = True
    y.explicit_start = explicit_start
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096  # never line-wrap scalars; wrapping is non-canonical churn
    return y


def _canonical_key(item: object) -> str:
    """Deterministic sort key: the item's own normalized YAML serialization.

    Dumping each item through the same emitter means two items that render
    identically sort adjacently and the order never depends on Python object
    identity or insertion order - only on content.
    """
    buf = io.StringIO()
    y = YAML()
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096
    try:
        y.dump(item, buf)
    except YAMLError:
        return repr(item)
    return buf.getvalue()


def _sort_node(node: object, sort_keys: bool, sort_sequences: bool) -> object:
    """Recursively alpha-sort mapping keys and canonical-sort sequence items.

    `sort_keys` / `sort_sequences` gate each axis independently so a file whose
    sequence order is load-bearing (pre-commit hooks, CI steps) can still get
    key-sort and canonical formatting without its lists being reordered.
    """
    if isinstance(node, CommentedMap):
        for key in list(node.keys()):
            node[key] = _sort_node(node[key], sort_keys, sort_sequences)
        if sort_keys:
            for key in sorted(node.keys(), key=str):
                node.move_to_end(key)  # carries the key's attached comments
        return node
    if isinstance(node, CommentedSeq):
        items = [_sort_node(c, sort_keys, sort_sequences) for c in node]
        if sort_sequences:
            items.sort(key=_canonical_key)
        node[:] = items
        return node
    if isinstance(node, dict):
        items = {k: _sort_node(node[k], sort_keys, sort_sequences) for k in node}
        return dict(sorted(items.items(), key=lambda kv: str(kv[0]))) if sort_keys else items
    if isinstance(node, list):
        out = [_sort_node(c, sort_keys, sort_sequences) for c in node]
        return sorted(out, key=_canonical_key) if sort_sequences else out
    return node


def _strip_comments(node: object) -> object:
    """Recursively drop every comment ruamel attached to a node, in place.

    A comment is not data, so clearing the comment attributes (.ca) leaves the
    parsed tree identical - the rewrite differs only in the absent comments.
    """
    if isinstance(node, (CommentedMap, CommentedSeq)):
        ca = getattr(node, "ca", None)
        if ca is not None:
            ca.items.clear()
            ca.comment = None
            ca.end = []
        children = node.values() if isinstance(node, CommentedMap) else node
        for child in children:
            _strip_comments(child)
    return node


def _scan_forbidden(text: str) -> list[str]:
    """Report anchors, aliases, and non-standard tags via the event stream."""
    problems: list[str] = []
    y = YAML()
    try:
        for event in y.parse(text):
            anchor = getattr(event, "anchor", None)
            if anchor:
                problems.append(f"anchor/alias &{anchor} or *{anchor} not allowed")
            tag = getattr(event, "tag", None)
            if isinstance(tag, str) and tag.startswith("!"):
                problems.append(f"non-standard tag {tag} not allowed")
    except YAMLError:
        pass  # a load error is reported separately by check_file
    # de-dup while keeping order
    seen: set[str] = set()
    return [p for p in problems if not (p in seen or seen.add(p))]


def check_file(path: Path, opts: "Options") -> tuple[bool, list[str]]:
    """Return (changed, problems). Rewrites `path` in place when fixable."""
    original = path.read_text(encoding="utf-8")
    problems: list[str] = []

    if opts.no_anchors:
        problems.extend(_scan_forbidden(original))

    y = _yaml(opts.explicit_start)
    try:
        data = y.load(original)
    except DuplicateKeyError as exc:
        problems.append(f"duplicate mapping key: {exc.problem or exc}".strip())
        return False, problems
    except YAMLError as exc:
        problems.append(f"not valid YAML: {exc}".strip())
        return False, problems

    if problems:  # anchors/tags present: fail without rewriting
        return False, problems

    if data is None:
        return False, []

    sort_sequences = opts.sort_sequences and not is_excluded(path, opts.order_significant)
    _sort_node(data, opts.sort_keys, sort_sequences)
    if opts.no_comments:
        _strip_comments(data)
    buf = io.StringIO()
    y.dump(data, buf)
    canonical = buf.getvalue()
    if not canonical.endswith("\n"):
        canonical += "\n"

    if canonical != original:
        path.write_text(canonical, encoding="utf-8")
        return True, []
    return False, []


def _should_skip(rel: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in rel.parts)


def _walk_repo() -> list[Path]:
    """Git-tracked YAML files, falling back to an rglob walk off-git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True,
            check=True,
            text=True,
            cwd=REPO_ROOT,
        )
        entries = [Path(e) for e in result.stdout.split("\x00") if e]
    except (subprocess.CalledProcessError, FileNotFoundError):
        entries = [
            p.relative_to(REPO_ROOT)
            for p in REPO_ROOT.rglob("*")
            if p.is_file()
        ]
    return entries


def _targets(args: list[str]) -> list[Path]:
    excludes = load_excludes(HOOK_ID)
    candidates = [Path(a) for a in args] if args else _walk_repo()
    out: list[Path] = []
    for p in candidates:
        rel = p if not p.is_absolute() else p
        if rel.suffix not in YAML_SUFFIXES:
            continue
        if _should_skip(rel) or is_excluded(rel, excludes):
            continue
        if not p.is_file():
            continue
        out.append(p)
    return sorted(set(out))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    opts = _load_options()
    changed = 0
    failed = 0
    for path in _targets(args):
        was_changed, problems = check_file(path, opts)
        if problems:
            failed += 1
            print(f"FAIL {path}")
            for problem in problems:
                print(f"  - {problem}")
        elif was_changed:
            changed += 1
            print(f"fixed {path}")
    if changed:
        print(
            f"\n{changed} file(s) rewritten to strict canonical form. "
            "Re-stage and commit.",
            file=sys.stderr,
        )
    if failed:
        print(
            f"{failed} file(s) have unfixable strictness violations (above).",
            file=sys.stderr,
        )
    return 1 if (changed or failed) else 0


if __name__ == "__main__":
    sys.exit(main())

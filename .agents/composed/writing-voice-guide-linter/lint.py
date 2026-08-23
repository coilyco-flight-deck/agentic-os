#!/usr/bin/env python3
"""Generic voice-guide linter. Rules come from a profile, never from here.

The engine owns matching, fence handling, reporting, and exit status. A profile
owns every value a house style could disagree about. See COMPOSED.md for the
profile contract.
"""
import json
import re
import sys
from pathlib import Path

CODE_FENCE = re.compile(r"^\s*```")
FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


class ProfileError(ValueError):
    """A profile that cannot be trusted to lint anything."""


def compile_rule(raw: dict, index: int) -> tuple:
    where = f"rules[{index}]"
    if not isinstance(raw, dict):
        raise ProfileError(f"{where}: each rule is an object")
    for key in ("id", "pattern", "hint"):
        if not isinstance(raw.get(key), str) or not raw[key]:
            raise ProfileError(f"{where}: {key} is a non-empty string")
    scope = raw.get("scope", "span")
    if scope not in ("span", "line"):
        raise ProfileError(f"{where}: scope is 'span' or 'line', got {scope!r}")
    flags = 0
    for flag in raw.get("flags", []):
        if flag not in FLAGS:
            raise ProfileError(f"{where}: unknown flag {flag!r}")
        flags |= FLAGS[flag]
    try:
        pattern = re.compile(raw["pattern"], flags)
    except re.error as error:
        raise ProfileError(f"{where}: {error}") from error
    return raw["id"], pattern, raw["hint"], scope


def load_profile(path: Path) -> list:
    """Rules from a JSON profile, or a ProfileError naming what is wrong.

    A profile that fails to load is never treated as zero rules: linting
    nothing and reporting success is the failure this refuses.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ProfileError(f"{path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ProfileError(f"{path}: {error}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("rules"), list):
        raise ProfileError(f"{path}: profile is an object with a 'rules' list")
    if not raw["rules"]:
        raise ProfileError(f"{path}: a profile with no rules lints nothing")
    return [compile_rule(rule, index) for index, rule in enumerate(raw["rules"])]


def lint_file(path: Path, rules: list) -> list:
    findings = []
    in_fence = False
    try:
        text = path.read_text(errors="ignore")
    except (IsADirectoryError, PermissionError, OSError):
        return findings
    for number, line in enumerate(text.splitlines(), start=1):
        if CODE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # A line-scoped hit reports once and stops, so a table row is not also
        # reported for every span rule its own punctuation happens to match.
        matched_line = False
        for name, pattern, hint, scope in rules:
            if scope != "line":
                continue
            if pattern.match(line):
                findings.append((path, number, name, line.strip()[:80], hint))
                matched_line = True
                break
        if matched_line:
            continue
        for name, pattern, hint, scope in rules:
            if scope == "line":
                continue
            for found in pattern.finditer(line):
                findings.append((path, number, name, found.group(0), hint))
    return findings


def resolve_targets(targets: list) -> list:
    paths = []
    for target in targets:
        path = Path(target)
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            paths.extend(sorted(path.rglob("*.md")))
    return paths


def main(argv: list | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in args
    args = [arg for arg in args if arg != "--strict"]
    profile_path = None
    if "--profile" in args:
        index = args.index("--profile")
        if index + 1 >= len(args):
            print("--profile needs a path", file=sys.stderr)
            return 2
        profile_path = Path(args[index + 1])
        del args[index : index + 2]
    if not profile_path or not args:
        print(
            "usage: lint.py --profile <profile.json> <file-or-dir>... [--strict]",
            file=sys.stderr,
        )
        return 2
    try:
        rules = load_profile(profile_path)
    except ProfileError as error:
        print(f"voice-lint: {error}", file=sys.stderr)
        return 2
    findings = []
    for path in resolve_targets(args):
        findings.extend(lint_file(path, rules))
    for path, line, name, span, hint in findings:
        print(f"{path}:{line}: [{name}] {span!r} - {hint}")
    return 1 if findings and strict else 0


if __name__ == "__main__":
    sys.exit(main())

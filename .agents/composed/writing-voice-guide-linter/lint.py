#!/usr/bin/env python3
"""Voice-guide linter for Kai's prose. See the skill entrypoint for rules."""
import re
import sys
from pathlib import Path

RULES = [
    ("em-dash", re.compile(r"—"), "replace with ' - '"),
    ("italics-asterisk", re.compile(r"(?<![\\\w*])\*[^\*\n]{1,200}\*(?!\*)"), "italics not allowed; bold sparingly"),
    ("italics-underscore", re.compile(r"(?<!\w)_[^_\n]{1,200}_(?!\w)"), "italics not allowed"),
    ("prose-semicolon", re.compile(r";"), "split into two sentences"),
    ("wrong-pronoun-he", re.compile(r"\b(he|him|his)\b", re.IGNORECASE), "if referring to Kai, use she/her/her"),
    ("wrong-pronoun-they", re.compile(r"\b(they|them|their)\b", re.IGNORECASE), "if referring to Kai, use she/her/her"),
    ("email-leak", re.compile(r"coilysiren@gmail\.com"), "leakable; allowed only in resume + website"),
]

CODE_FENCE = re.compile(r"^\s*```")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")


def lint_file(path: Path) -> list:
    findings = []
    in_fence = False
    try:
        text = path.read_text(errors="ignore")
    except (IsADirectoryError, PermissionError):
        return findings
    for i, line in enumerate(text.splitlines(), start=1):
        if CODE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if TABLE_ROW.match(line):
            findings.append((path, i, "prose-table", line.strip()[:80], "use flat bullets per voice guide"))
            continue
        for name, pattern, hint in RULES:
            for m in pattern.finditer(line):
                findings.append((path, i, name, m.group(0), hint))
    return findings


def main():
    args = sys.argv[1:]
    strict = "--strict" in args
    targets = [a for a in args if a != "--strict"]
    if not targets:
        print("usage: lint.py <file-or-dir>... [--strict]", file=sys.stderr)
        sys.exit(2)
    paths = []
    for t in targets:
        p = Path(t)
        if p.is_file():
            paths.append(p)
        elif p.is_dir():
            paths.extend(sorted(p.rglob("*.md")))
    findings = []
    for p in paths:
        findings.extend(lint_file(p))
    for path, line, name, span, hint in findings:
        print(f"{path}:{line}: [{name}] {span!r} - {hint}")
    if findings and strict:
        sys.exit(1)


if __name__ == "__main__":
    main()

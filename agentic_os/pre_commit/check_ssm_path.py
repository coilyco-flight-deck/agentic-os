#!/usr/bin/env python3
"""Validate SSM parameter paths against the /<org>/<repo>/<tier>/<tail> schema.

Schema (coilysiren fleet):

    /<org>/<repo>/<tier>/<tail>

    org   controlled vocabulary; currently the literal "coilysiren"
    repo  lowercase repo slug, [a-z0-9-]+
    tier  access tier: admin | write | read
    tail  freeform leaf, [a-z0-9-]+ (single segment, no further slashes)

Exactly four segments, leading slash, every segment lowercase. The tier
segment is load-bearing: IAM gates on parameter/*/*/<tier>/* and the per-tier
KMS keys wrap by the same position, so a malformed path silently falls outside
every tier policy instead of failing loudly. Validating the shape up front is
the cheap guard against that.

Usage:
    check-ssm-path /coilysiren/backend/write/ts-authkey [more paths...]
    check-ssm-path --stdin    # one path per line on stdin

Origin: SSM path-tier convention (coilysiren fleet).
"""

from __future__ import annotations

import re
import sys

ALLOWED_ORGS = ("coilysiren",)
TIERS = ("admin", "write", "read")
SEGMENT_RE = re.compile(r"^[a-z0-9-]+$")


def validate_path(path: str) -> list[str]:
    """Return a list of human-readable problems with `path`. Empty means valid."""
    if not path.startswith("/"):
        return [f"must start with '/' (got {path!r})"]

    segments = path[1:].split("/")
    if len(segments) != 4:
        return [
            "expected 4 segments /<org>/<repo>/<tier>/<tail>, "
            f"got {len(segments)} in {path!r}"
        ]

    org, repo, tier, tail = segments
    problems: list[str] = []
    if org not in ALLOWED_ORGS:
        problems.append(f"org {org!r} not in allowed orgs {list(ALLOWED_ORGS)}")
    if not SEGMENT_RE.match(repo):
        problems.append(f"repo {repo!r} must match [a-z0-9-]+")
    if tier not in TIERS:
        problems.append(f"tier {tier!r} must be one of {list(TIERS)}")
    if not SEGMENT_RE.match(tail):
        problems.append(f"tail {tail!r} must match [a-z0-9-]+ (single segment)")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--stdin" in args:
        args.remove("--stdin")
        args += [line.strip() for line in sys.stdin if line.strip()]

    if not args:
        print("usage: check-ssm-path /<org>/<repo>/<tier>/<tail> [more...]", file=sys.stderr)
        return 2

    failed = 0
    for path in args:
        problems = validate_path(path)
        if problems:
            failed += 1
            print(f"FAIL {path}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"ok   {path}")

    if failed:
        print(
            f"\n{failed} path(s) failed the /<org>/<repo>/<tier>/<tail> schema.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

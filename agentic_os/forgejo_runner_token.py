"""Scope router for Forgejo runner registration-token fetch overlays."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


USAGE = "usage: generate-runner-token global | org <org> | repo <owner> <repo>"


@dataclass(frozen=True)
class Scope:
    leaf: str
    argv: tuple[str, ...]


def parse_scope(argv: list[str]) -> Scope:
    if not argv:
        raise ValueError(USAGE)

    scope, *rest = argv
    if scope == "global":
        if rest:
            raise ValueError(USAGE)
        return Scope("generate-runner-token-global", ())
    if scope == "org":
        if len(rest) != 1:
            raise ValueError(USAGE)
        return Scope("generate-runner-token-org", (rest[0],))
    if scope == "repo":
        if len(rest) != 2:
            raise ValueError(USAGE)
        return Scope("generate-runner-token-repo", (rest[0], rest[1]))
    raise ValueError(USAGE)


def main(argv: list[str] | None = None) -> int:
    scope = parse_scope(list(sys.argv[1:] if argv is None else argv))
    cmd = ["ward", "ops", "forgejo", "fetch", scope.leaf, *scope.argv]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

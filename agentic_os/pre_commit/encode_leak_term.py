#!/usr/bin/env python3
"""Encode a term to hex for the leak-guard ruleset, and round-trip it back.

The ruleset never stores plaintext, so a plain `rg <term>` over it finds nothing,
and its own config has to honour that. With no `--term` this reads one line from
stdin, so a sensitive term never lands in shell history as an argv token.
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="hex-encode a leak-guard term")
    parser.add_argument("--term", help="term to encode (avoid for secrets - argv is logged)")
    parser.add_argument("--decode", help="hex to decode back to text (round-trip check)")
    args = parser.parse_args()

    if args.decode is not None:
        try:
            text = bytes.fromhex(args.decode.strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            sys.stderr.write(f"leak-guard-encode: not valid hex: {exc}\n")
            return 2
        sys.stdout.write(text + "\n")
        return 0

    term = args.term if args.term is not None else sys.stdin.readline().rstrip("\n")
    if not term:
        sys.stderr.write("leak-guard-encode: empty term\n")
        return 2
    sys.stdout.write(term.encode("utf-8").hex() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

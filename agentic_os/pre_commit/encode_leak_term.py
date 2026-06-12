#!/usr/bin/env python3
"""Encode a term to hex for the leak-guard ruleset (and round-trip back).

The leak-guard ruleset never stores plaintext: every banned term lives as
lowercase hex, so a plain `rg <term>` over the ruleset - or anywhere else -
finds nothing. That is the whole point of the guard, so its own config must
honor it too. This helper turns a term into that hex (and back) without the
plaintext landing in shell history: with no `--term` it reads one line from
stdin, so a sensitive term can be typed or piped, never typed as an argv token.

Usage:
    leak-guard-encode                 # read one line from stdin, print hex
    leak-guard-encode --term agentic  # encode argv token (lands in history)
    leak-guard-encode --decode 6b6170 # round-trip a hex term back to text
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

#!/usr/bin/env python3
"""Lint ~/.aws/config for the [profile default] trap.

Background: AWS SDK default-profile resolution reads `[default]`, never
`[profile default]`. The `[profile X]` form is reserved for non-default
profiles. So `region = ...` placed under `[profile default]` is unreachable
and SDK calls fall back to "NoRegion: You must specify a region".

STS-only preflights (sts get-caller-identity) hide the bug because STS is a
global endpoint and doesn't need a region. SSM, S3, and friends will fail.

This check parses ~/.aws/config (or $AWS_CONFIG_FILE) and exits non-zero if
it finds a `[profile default]` section, printing the remediation.

Run via `make check-aws-config` or `coily exec check-aws-config`.

Origin: coilysiren/agentic-os-kai#416.
"""

from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path


def config_path() -> Path:
    override = os.environ.get("AWS_CONFIG_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".aws" / "config"


def main() -> int:
    path = config_path()
    if not path.exists():
        print(f"ok: {path} does not exist, nothing to lint")
        return 0

    parser = configparser.RawConfigParser()
    try:
        parser.read(path)
    except configparser.Error as exc:
        print(f"error: failed to parse {path}: {exc}", file=sys.stderr)
        return 2

    has_profile_default = parser.has_section("profile default")

    if not has_profile_default:
        print(f"ok: {path} has no [profile default] trap")
        return 0

    profile_default_keys = dict(parser.items("profile default"))
    default_keys = dict(parser.items("default")) if parser.has_section("default") else {}

    print(f"fail: {path} contains [profile default], which the AWS SDK ignores for default lookups.")
    print()
    print("Keys currently stranded under [profile default]:")
    for k, v in profile_default_keys.items():
        print(f"  {k} = {v}")
    if default_keys:
        print()
        print("Keys already in [default] (kept as-is):")
        for k, v in default_keys.items():
            print(f"  {k} = {v}")
    print()
    print("Fix: merge into a single [default] section. Example:")
    print()
    merged = {**profile_default_keys, **default_keys}
    print("  [default]")
    for k, v in merged.items():
        print(f"  {k} = {v}")
    print()
    print("Background: coilysiren/agentic-os-kai#416.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

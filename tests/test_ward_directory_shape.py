from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# AGENTS.md: AOS ships no Ward role-policy or KDL bundle. This outlived the
# `ward doctor` suite that used to carry it. See docs/ward-specs.md.
def test_ward_directory_has_no_retired_kdl_configuration() -> None:
    assert not list((ROOT / ".ward").glob("*.kdl"))

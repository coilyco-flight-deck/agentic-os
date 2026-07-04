"""Tests for the canonical agent-id generator, its vector, and the org map.

The drift test (`test_committed_vectors_match_module`) is the load-bearing one:
it regenerates the vector from the module and byte-compares against the committed
`agent_id_vectors.json`, so any alphabet or algorithm change that forgets to
re-emit the file fails CI - the cross-language contract cli-guard #177 ports
against cannot silently drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_os import agent_id


def test_new_id_shape() -> None:
    for _ in range(500):
        cid = agent_id.new_id()
        assert len(cid) == agent_id.ID_LEN
        assert cid.islower()
        assert all(c in agent_id.ID_LETTERS for c in cid[: agent_id.ID_LETTER_LEN])
        assert all(c in agent_id.ID_DIGITS for c in cid[agent_id.ID_LETTER_LEN :])


def test_alphabet_excludes_confusable_characters() -> None:
    # Lifted from the o2r source / docs/dictatable-id-alphabet.md: the eight
    # dropped characters must never appear in the alphabet.
    for bad in ["i", "l", "o", "n", "0", "1", "2", "3"]:
        assert bad not in agent_id.ID_ALPHABET
    assert agent_id.ID_LETTERS == "abcdefghjkmpqrstuvwxyz"
    assert agent_id.ID_DIGITS == "456789"


def test_is_valid() -> None:
    # Note: excluded digits (0-3) fail even in the right shape, so the issue's
    # illustrative "ab81"/"cd92" examples are themselves invalid ids.
    assert agent_id.is_valid("ab85")
    assert not agent_id.is_valid("ab81")  # '1' is an excluded digit
    assert not agent_id.is_valid("AB85")  # uppercase is not canonical
    assert not agent_id.is_valid("ab8")  # too short
    assert not agent_id.is_valid("abcd")  # no digits
    assert not agent_id.is_valid("8945")  # no leading letters
    assert not agent_id.is_valid("ao85")  # confusable 'o' rejected
    assert not agent_id.is_valid("a8b5")  # interleaved


def test_normalize_trims_and_lowercases() -> None:
    assert agent_id.normalize("  AB85 ") == "ab85"
    assert agent_id.normalize("Cd97") == "cd97"
    with pytest.raises(ValueError):
        agent_id.normalize("nope")


def test_seeded_id_is_deterministic() -> None:
    assert agent_id.seeded_id("kai-server") == agent_id.seeded_id("kai-server")
    assert agent_id.is_valid(agent_id.seeded_id("anything"))


def test_committed_vectors_match_module() -> None:
    committed = Path(agent_id._VECTORS_PATH).read_text(encoding="utf-8")
    assert committed == agent_id._dumped_vectors(), (
        "agent_id_vectors.json is stale - regenerate with "
        "`python -m agentic_os.agent_id --emit-vectors`"
    )
    data = json.loads(committed)
    assert data["id_letters"] == agent_id.ID_LETTERS
    assert data["id_digits"] == agent_id.ID_DIGITS
    for vec in data["vectors"]:
        assert agent_id.seeded_id(vec["seed"]) == vec["id"]
        assert agent_id.is_valid(vec["id"])


def test_org_shortname_mappings_and_fallback() -> None:
    assert agent_id.org_shortname("coilyco-flight-deck") == "flight"
    assert agent_id.org_shortname("coilyco-gaming") == "gaming"
    assert agent_id.org_shortname("coilyco-bridge") == "bridge"
    # Unmapped -> last '-' segment; no dash -> the org verbatim.
    assert agent_id.org_shortname("some-long-org") == "org"
    assert agent_id.org_shortname("solo") == "solo"


def test_org_shortnames_file_has_documented_shape() -> None:
    data = agent_id.load_org_shortnames()
    assert data["map"]["coilyco-flight-deck"] == "flight"
    assert data["fallback"] == "last-dash-segment"

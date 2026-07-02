import pathlib


SPEC_DIR = pathlib.Path(__file__).resolve().parents[1] / "ward-specs"
TOKENS = ("coilysiren", "coilyco")


def test_ward_specs_bundle_has_no_coilyco_values() -> None:
    seen = 0
    for path in SPEC_DIR.iterdir():
        if path.suffix not in {".kdl", ".json"}:
            continue
        seen += 1
        body = path.read_text()
        lower = body.lower()
        for token in TOKENS:
            assert token not in lower, f"{path.name} carries {token}"
    assert seen > 0


def test_ward_specs_fleet_parses() -> None:
    body = (SPEC_DIR / "ward-kdl.fleet.kdl").read_text()
    assert "fleet {" in body
    assert "schema-version 2" in body
    assert "agent claude" in body
    assert "agent codex" in body
    assert "agent opencode" in body
    assert "agent goose" in body

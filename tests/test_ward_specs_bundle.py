import pathlib


SPEC_DIR = pathlib.Path(__file__).resolve().parents[1] / ".ward"


def test_ward_specs_bundle_carries_deployment_anchors() -> None:
    # This is the coilyco deployment bundle (ward#453), so it must carry the
    # deployment anchors ward compiles in. See docs/ward-specs.md.
    forgejo = (SPEC_DIR / "ward-kdl.forgejo.guardfile.kdl").read_text()
    assert "forgejo.coilysiren.me" in forgejo
    assert '/forgejo/coilyco-ops/api-token' in forgejo
    assert "restrict owner matches coily*" in forgejo

    signoz = (SPEC_DIR / "ward-kdl.signoz.guardfile.kdl").read_text()
    assert "/coilysiren/signoz-ser8/api-token" in signoz

    ollama = (SPEC_DIR / "ward-kdl.ollama.guardfile.kdl").read_text()
    assert "/coilysiren/ollama/host" in ollama

    defaults = (SPEC_DIR / "ward-kdl.defaults.kdl").read_text()
    assert 'agent-workflow default="direct-main"' in defaults
    assert (
        'repo "coilyco-flight-deck/ward" workflow="pull-requests-and-merge"'
        in defaults
    )
    assert "workflow=pr" not in defaults
    assert 'default=pr' not in defaults

    fleet = (SPEC_DIR / "ward-kdl.fleet.kdl").read_text()
    assert "attribution name=coilyco-ops" in fleet


def test_ward_specs_fleet_parses() -> None:
    body = (SPEC_DIR / "ward-kdl.fleet.kdl").read_text()
    assert "fleet {" in body
    assert "schema-version 2" in body
    assert "agent claude" in body
    assert "agent codex" in body
    assert "agent opencode" in body
    assert "agent goose" in body


def test_ward_specs_bundle_defaults_are_packaged() -> None:
    release = (
        pathlib.Path(__file__).resolve().parents[1]
        / ".forgejo"
        / "workflows"
        / "release.yml"
    ).read_text()
    assert "./ward-kdl.defaults.kdl" in release

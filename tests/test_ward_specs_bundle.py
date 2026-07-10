import pathlib


SPEC_DIR = pathlib.Path(__file__).resolve().parents[1] / ".ward"


def test_ward_specs_bundle_carries_deployment_anchors() -> None:
    # This is the coilyco deployment bundle (ward#453), so it must carry the
    # deployment anchors ward compiles in. See docs/ward-specs.md.
    forgejo = (SPEC_DIR / "ward-kdl.forgejo.guardfile.kdl").read_text()
    assert "forgejo.coilysiren.me" in forgejo
    assert '/forgejo/coilyco-ops/api-token' in forgejo
    assert "restrict owner matches coily*" in forgejo
    assert "can dispatch workflow" in forgejo

    actions = (SPEC_DIR / "ward-kdl.forgejo.actions.guardfile.kdl").read_text()
    assert 'can run "actions logs"' in actions
    assert 'when arg0 matches coily*' in actions
    assert '.ward/forgejo-actions-logs.sh' in actions

    bridge = (SPEC_DIR / "forgejo-actions-logs.sh").read_text()
    assert "/actions/runs/${run_index}/jobs/${job_index}/attempt/${attempt}/logs" in bridge
    assert "Authorization: token ${FORGEJO_TOKEN}" in bridge

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
    assert "default=pr" not in defaults

    fleet = (SPEC_DIR / "ward-kdl.fleet.kdl").read_text()
    assert "attribution name=coilyco-ops" in fleet


def test_ward_specs_bundle_documents_workflow_dispatch() -> None:
    docs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "docs"
        / "ward-ops-forgejo-reference.md"
    ).read_text()
    assert "workflow dispatch" in docs
    assert "/actions/workflows/{workflowfilename}/dispatches" in docs
    assert "--ref" in docs
    assert "actions logs" in docs
    assert "forgejo-actions-logs.sh" in docs


def test_ward_specs_docs_reference_live_config_source() -> None:
    docs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "docs"
        / "ward-specs.md"
    ).read_text()
    assert "WARD_CONFIG_REF" in docs
    assert "launch through `WARD_CONFIG_REF`" in docs


def test_ward_specs_docs_cover_actions_log_streaming() -> None:
    docs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "docs"
        / "forgejo-actions-logs.md"
    ).read_text()
    assert "ward ops forgejo actions logs" in docs
    assert "GET /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job}/attempt/{attempt}/logs" in docs
    assert "JSON-render" in docs


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
    assert "./ward-kdl.forgejo.actions.guardfile.kdl" in release
    assert "./forgejo-actions-logs.sh" in release

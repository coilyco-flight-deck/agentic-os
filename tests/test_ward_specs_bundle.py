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
    assert "can rerun run" not in forgejo
    assert "can rerun-failed-jobs run" not in forgejo

    read = (SPEC_DIR / "ward-kdl.forgejo.read.guardfile.kdl").read_text()
    assert "wrap ward-kdl-read ops forgejo" in read
    assert "can get issue" in read
    assert "never delete issue" in read

    write = (SPEC_DIR / "ward-kdl.forgejo.write.guardfile.kdl").read_text()
    assert 'inherit "../ward-kdl-read/ward-kdl.forgejo.read.guardfile.kdl"' in write
    assert "can create issue" in write
    assert "can comment issue" in write

    admin = (SPEC_DIR / "ward-kdl.forgejo.admin.guardfile.kdl").read_text()
    assert 'inherit "../ward-kdl-write/ward-kdl.forgejo.write.guardfile.kdl"' in admin
    assert "can delete repo" in admin
    assert "can delete issue-comment" in admin
    assert "can rerun run" not in admin
    assert "can rerun-failed-jobs run" not in admin

    actions = (SPEC_DIR / "ward-kdl.forgejo.logs.guardfile.kdl").read_text()
    assert 'can run "actions logs"' in actions
    assert 'when arg0 matches coily*' in actions
    assert '.ward/forgejo-actions-logs.sh' in actions

    bridge = (SPEC_DIR / "forgejo-actions-logs.sh").read_text()
    assert "python3 -m agentic_os.forgejo_actions_logs" in bridge

    rerun = (SPEC_DIR / "ward-kdl.forgejo.rerun.guardfile.kdl").read_text()
    assert 'when arg0 matches coily*' in rerun
    assert '/forgejo/api-token' in rerun
    assert '.ward/forgejo-actions-rerun.sh' in rerun
    assert '.ward/forgejo-actions-rerun-failed-jobs.sh' in rerun

    rerun_bridge = (SPEC_DIR / "forgejo-actions-rerun.sh").read_text()
    assert "python3 -m agentic_os.forgejo_actions_rerun rerun" in rerun_bridge

    rerun_failed_bridge = (
        SPEC_DIR / "forgejo-actions-rerun-failed-jobs.sh"
    ).read_text()
    assert "python3 -m agentic_os.forgejo_actions_rerun rerun-failed-jobs" in rerun_failed_bridge

    aws = (SPEC_DIR / "ward-kdl.aws.guardfile.kdl").read_text()
    assert "wrap ward-kdl ops aws" in aws
    assert "can run ssm get-parameter" in aws

    kubectl = (SPEC_DIR / "ward-kdl.kubectl.guardfile.kdl").read_text()
    assert "wrap ward-kdl ops kubectl" in kubectl
    assert "can run apply" in kubectl

    roles = (SPEC_DIR / "ward-kdl.roles.kdl").read_text()
    assert "role qa" in roles
    assert "role ops" in roles
    assert "capabilities read ops" in roles

    defaults = (SPEC_DIR / "ward-kdl.defaults.kdl").read_text()
    assert "repo-authority default=forgejo" in defaults
    assert "trusted-owner coilysiren" in defaults
    assert "trusted-owner coilyco-flight-deck" in defaults
    assert 'repo "coilysiren/*" forge=github' in defaults
    assert 'repo "coilyco-flight-deck/*" forge=forgejo' in defaults
    assert 'agent-workflow default="direct-main"' in defaults
    assert 'repo "coilyco-flight-deck/cli-guard" workflow="pull-requests-and-merge"' in defaults
    assert 'repo "coilyco-flight-deck/ward" workflow="pull-requests-and-merge"' in defaults
    assert 'repo "coilyco-flight-deck/agentic-os" workflow="pull-requests-and-merge"' in defaults
    assert "workflow=pr" not in defaults
    assert "default=pr" not in defaults

    fleet = (SPEC_DIR / "ward-kdl.fleet.kdl").read_text()
    assert "attribution name=coilyco-ops" in fleet


def test_shell_core_exports_the_ward_bundle_ref() -> None:
    shell = (
        pathlib.Path(__file__).resolve().parents[1] / "shell" / "common.sh"
    ).read_text()
    assert "_siren_ward_config_ref()" in shell
    assert 'git -C "$repo" rev-parse HEAD' in shell
    assert 'export WARD_CONFIG_REF="$(_siren_ward_config_ref)"' in shell


def test_ward_specs_bundle_documents_workflow_dispatch() -> None:
    docs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "docs"
        / "ward-ops-forgejo-reference.md"
    ).read_text()
    assert "workflow dispatch" in docs
    assert "/actions/workflows/{workflowfilename}/dispatches" in docs
    assert "--ref" in docs
    assert "ward ops forgejo pr view" in docs
    assert "/repos/{owner}/{repo}/pulls/{index}" in docs
    assert "ward ops forgejo pr list" in docs


def test_ward_specs_bundle_documents_actions_rerun() -> None:
    docs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "docs"
        / "ward-ops-forgejo-reference.md"
    ).read_text()
    lock = (SPEC_DIR / "forgejo.swagger.lock.json").read_text()
    assert "ward ops forgejo run rerun" in docs
    assert "ward ops forgejo run rerun-failed-jobs" in docs
    assert "/actions/runs/{run_id}/rerun" in docs
    assert "/actions/runs/{run_id}/rerun-failed-jobs" in docs
    assert "Auth source: admin PAT from `/forgejo/api-token`" in docs
    forgejo = (SPEC_DIR / "ward-kdl.forgejo.rerun.guardfile.kdl").read_text()
    assert "can rerun run" in forgejo
    assert "can rerun-failed-jobs run" in forgejo
    assert '"rerunWorkflowRun"' not in lock
    assert '"rerunFailedWorkflowRun"' not in lock
    assert '"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"' not in lock
    assert '"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs"' not in lock


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
    assert "same-path exec overlays are skipped fail-closed" in docs
    assert "ward#950" in docs
    assert "/actions/runs/886/jobs/0" in docs
    assert "data-run-id" in docs
    assert "GET /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job}/attempt/{attempt}/logs" in docs
    assert "plaintext log stream" in docs


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
    assert "./ward-kdl.forgejo.read.guardfile.kdl" in release
    assert "./ward-kdl.forgejo.write.guardfile.kdl" in release
    assert "./ward-kdl.forgejo.admin.guardfile.kdl" in release
    assert "./ward-kdl.forgejo.logs.guardfile.kdl" in release
    assert "./forgejo-actions-logs.sh" in release
    assert "./ward-kdl.forgejo.actions.guardfile.kdl" not in release

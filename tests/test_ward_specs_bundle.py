import pathlib
import re


SPEC_DIR = pathlib.Path(__file__).resolve().parents[1] / ".ward"


def _roles_binding(roles_text: str, guardfile: str) -> set[str]:
    bound: set[str] = set()
    for block in re.split(r"\n\s*role\s+", roles_text)[1:]:
        if f'guardfile "{guardfile}"' in block:
            bound.add(block.split(maxsplit=1)[0])
    return bound


def test_ward_specs_bundle_carries_deployment_anchors() -> None:
    # This is the coilyco deployment bundle (ward#453), so it must carry the
    # deployment anchors ward compiles in. See docs/ward-specs.md.
    forgejo = (SPEC_DIR / "guardfile.forgejo.kdl").read_text()
    assert "forgejo.coilysiren.me" in forgejo
    assert "/forgejo/coilyco-ops/api-token" in forgejo
    assert "restrict owner matches coily*" in forgejo
    assert "can dispatch workflow" in forgejo

    read = (SPEC_DIR / "guardfile.forgejo.read.kdl").read_text()
    assert "wrap ward-kdl-read ops forgejo" in read
    assert "can get issue" in read
    assert "never delete issue" in read

    write = (SPEC_DIR / "guardfile.forgejo.write.kdl").read_text()
    assert 'inherit "../guardfile.forgejo.read.kdl"' in write
    assert "can create issue" in write
    assert "can comment issue" in write

    admin = (SPEC_DIR / "guardfile.forgejo.admin.kdl").read_text()
    assert 'inherit "../guardfile.forgejo.write.kdl"' in admin
    assert "can delete repo" in admin
    assert "can delete issue-comment" in admin

    actions = (SPEC_DIR / "guardfile.forgejo.readactions.kdl").read_text()
    assert 'can run "actions logs"' in actions
    assert 'can run "actions runs"' in actions
    assert 'can run "actions tasks"' in actions
    assert 'when arg0 matches coily*' in actions
    assert '.ward/forgejo-actions-logs.sh' in actions
    assert '.ward/forgejo-actions-list.sh' in actions

    bundle_manifest = (SPEC_DIR / "ward.bundle.kdl").read_text()
    assert "ops {" in bundle_manifest
    assert 'forgejo "ops.forgejo.kdl"' in bundle_manifest

    ops_guardfile = (SPEC_DIR / "ops.forgejo.kdl").read_text()
    assert "wrap ward-kdl ops forgejo" in ops_guardfile
    assert "spec forgejo.swagger.v1.json" in ops_guardfile

    lockfile = (SPEC_DIR / "forgejo.swagger.lock.json").read_text()
    assert '"basePath": "/api/v1"' in lockfile
    assert '"definitions": {' in lockfile

    merge = (SPEC_DIR / "guardfile.forgejo.merge.kdl").read_text()
    assert "wrap ward-kdl-merge ops forgejo" in merge
    assert "restrict owner matches coily*" in merge
    assert "op repoMergePullRequest" in merge
    assert "op repoPullRequestIsMerged" in merge

    guardfile = (SPEC_DIR / "guardfile.forgejo.kdl").read_text()
    assert "action list tasks {" in guardfile
    assert 'describe "list Forgejo Actions tasks with a safe page-1 default"' in guardfile
    assert 'page "1"' in guardfile
    assert "limit $limit" in guardfile

    bridge = (SPEC_DIR / "forgejo-actions-logs.sh").read_text()
    assert "python3 -m agentic_os.forgejo_actions_logs" in bridge

    aws = (SPEC_DIR / "guardfile.aws.kdl").read_text()
    assert "wrap ward-kdl ops aws" in aws
    assert "can run ssm get-parameter" in aws

    listing = (SPEC_DIR / "forgejo-actions-list.sh").read_text()
    assert "/actions/${kind}?page=${page}" in listing
    assert "page=1" in listing
    assert "kind must be runs or tasks" in listing

    kubectl = (SPEC_DIR / "guardfile.kubectl.kdl").read_text()
    assert "wrap ward-kdl ops kubectl" in kubectl
    assert "can run apply" in kubectl

    roles = (SPEC_DIR / "roles.kdl").read_text()
    assert "role qa" in roles
    assert "role ops" in roles
    assert "capabilities read ops" not in roles
    assert 'guardfile "guardfile.forgejo.read.kdl"' in roles
    assert 'guardfile "guardfile.forgejo.readactions.kdl"' in roles
    # Merge authority is the surface worth pinning by name, not by count: engineer
    # and director land code, pm merges what it triages (agentic-os#446).
    assert _roles_binding(roles, "guardfile.forgejo.merge.kdl") == {"engineer", "director", "pm"}
    # aws/ssm reach stays off the code-landing roles except engineer's scoped read.
    assert _roles_binding(roles, "guardfile.aws.kdl") == {"director", "advisor", "ops"}
    assert 'guardfile "guardfile.aws.kdl"' in roles
    assert 'guardfile "guardfile.kubectl.kdl"' in roles

    defaults = (SPEC_DIR / "defaults.kdl").read_text()
    assert "defaults {" in defaults
    assert 'agent-workflow default="direct-main"' in defaults
    assert 'repo "coilyco-flight-deck/cli-guard" workflow="pull-requests-and-merge"' in defaults
    assert 'repo "coilyco-flight-deck/ward" workflow="pull-requests-and-merge"' in defaults
    assert 'repo "coilyco-flight-deck/agentic-os" workflow="pull-requests-and-merge"' in defaults
    assert "repo-authority" not in defaults
    assert "workflow=pr" not in defaults
    assert "default=pr" not in defaults
    # ward's embedded smart-defaults are the product defaults; this bundle only
    # overlays them. Restating a tuning key here shadows ward and rots (aos#452).
    for product_default in (
        "agent-reservation-ttl",
        "agent-reservation-recheck-max",
        "agent-reap-idle",
        "agent-reap-max-cpu",
        "director-max-parallel",
        "director-limit",
        "director-poll-interval",
        "reviewer-timeout",
        "config-bundle-ttl",
        "container-assets-ttl",
        "container-reap-keep",
    ):
        assert f"\n    {product_default} " not in defaults, f"{product_default} is ward's default, not the deployment bundle's"

    repos = (SPEC_DIR / "repos.kdl").read_text()
    assert "repos {" in repos
    assert "trusted-owner coilysiren" in repos
    assert "trusted-owner coilyco-flight-deck" in repos
    assert 'repo "coilysiren/*" forge=github' in repos
    assert 'repo "coilyco-flight-deck/*" forge=forgejo' in repos
    # KDL v2 spells booleans #true / #false. Bare true / false parse as identifiers
    # and fail the whole document, degrading ward's exec mount (regression: 778666c).
    assert "burndown default=#true" in repos
    assert 'repo "coilyco-flight-deck/infrastructure" #false' in repos
    assert 'repo "coilyco-bridge/deploy" #false' in repos
    assert not re.search(r"=(?:true|false)\b", repos)

    agents = (SPEC_DIR / "agents.kdl").read_text()
    assert "agents {" in agents
    assert "attribution name=coilyco-ops" in agents
    assert "role engineer" not in agents

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
    assert "ward ops forgejo tasks list" in docs
    assert "safe page-1 default" in docs
    # The injected page=1 arg literal stays pinned in the guardfile-anchor
    # test ('page "1"'); the v0.584.0 renderer no longer prints call args.
    assert "ward ops forgejo commit status" in docs
    assert "ward ops forgejo action-run list" in docs


def test_ward_specs_docs_cover_actions_listing() -> None:
    docs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "docs"
        / "forgejo-actions-listing.md"
    ).read_text()
    assert "defaults to `page=1`" in docs
    assert "ward ops forgejo actions runs" in docs
    assert "ward ops forgejo actions tasks" in docs
    assert "page=1&limit=1" in docs


def test_ward_specs_docs_reference_live_config_source() -> None:
    docs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "docs"
        / "ward-specs.md"
    ).read_text()
    assert "WARD_CONFIG_REF" in docs
    assert "launch through `WARD_CONFIG_REF`" in docs
    assert "release-time build overlay is gone" in docs


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
    body = (SPEC_DIR / "agents.kdl").read_text()
    assert "agents {" in body
    assert "schema-version 2" in body
    assert "agent claude" in body
    assert "agent codex" in body
    assert "agent opencode" in body
    assert "agent goose" in body


def test_ward_specs_roles_parse() -> None:
    body = (SPEC_DIR / "roles.kdl").read_text()
    assert "roles {" in body
    assert body.count('guardfile "') >= 10
    assert "        guardfiles " not in body


def test_ward_specs_bundle_defaults_are_packaged() -> None:
    release = (
        pathlib.Path(__file__).resolve().parents[1]
        / ".forgejo"
        / "workflows"
        / "release.yml"
    ).read_text()
    assert "./agents.kdl" in release
    assert "./defaults.kdl" in release
    assert "./guardfile.aws.kdl" in release
    assert "./guardfile.forgejo.read.kdl" in release
    assert "./guardfile.forgejo.write.kdl" in release
    assert "./guardfile.forgejo.admin.kdl" in release
    assert "./guardfile.forgejo.readactions.kdl" in release
    assert "./guardfile.forgejo.kdl" in release
    assert "./guardfile.forgejo.merge.kdl" in release
    assert "./guardfile.kubectl.kdl" in release
    assert "./repos.kdl" in release
    assert "./roles.kdl" in release
    assert "./forgejo-actions-rerun-failed-jobs.sh" in release
    assert "./forgejo-actions-rerun.sh" in release
    assert "./forgejo-runner-token.sh" in release
    assert "./surface-check.sh" in release
    assert "./guardfile.forgejo.runnertoken.kdl" in release
    assert "./guardfile.tailscale.kdl" in release
    assert "./ward-kdl.forgejo.rerun.guardfile.kdl" in release
    assert "./forgejo.swagger.lock.json" not in release
    assert "./forgejo-actions-list.sh" in release
    assert "./forgejo-actions-logs.sh" in release
    assert "./ward.bundle.kdl" not in release
    assert "./ops.forgejo.kdl" not in release
    assert "./ward-kdl.forgejo.actions.guardfile.kdl" not in release

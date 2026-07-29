from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_pull_request_ci_workflow_exposes_branch_protection_context() -> None:
    workflow = (ROOT / ".forgejo" / "workflows" / "ci.yml").read_text()
    assert "name: ci" in workflow
    assert "pull_request:" in workflow
    assert workflow.count("scripts/install-workflow-ward.sh") == 2
    assert "WARD_WORKFLOW_VERSION" not in workflow
    assert "build-dev-base:" in workflow
    assert "runs-on: docker-build" in workflow
    assert "uses: ./actions/dev-base-build" in workflow
    assert "base-sha: ${{ github.event.pull_request.base.sha }}" in workflow


def test_pull_request_image_validation_has_no_publish_credential() -> None:
    workflow = (ROOT / ".forgejo" / "workflows" / "ci.yml").read_text()
    image_job = workflow.split("  build-dev-base:", 1)[1]

    assert "github.event_name == 'pull_request'" in image_job
    assert "secrets." not in image_job
    assert "REGISTRY_TOKEN" not in image_job
    assert "--push" not in image_job


def test_pull_request_ci_docs_name_the_required_context() -> None:
    docs = (ROOT / "docs" / "ci-in-dev-base.md").read_text()
    assert "ci / gate" in docs
    assert "ci / build-dev-base" in docs
    assert "pull-request-and-merge" in docs


def test_promote_workflow_uses_the_same_repo_gate_as_ci() -> None:
    workflow = (ROOT / ".forgejo" / "workflows" / "promote.yml").read_text()
    gate = (ROOT / "scripts" / "ci" / "repo-test-gate.sh").read_text()
    assert "name: promote" in workflow
    assert "scripts/ci/repo-test-gate.sh" in workflow
    assert "uv run pytest" in gate
    assert "pre-commit run --all-files" in gate
    assert "Install validated ward for repo gate" in workflow
    assert "Load the .ward bundle with the updated ward" not in workflow
    assert "ward exec test" not in workflow
    assert "Install ward from source with workflow bundle support" not in workflow

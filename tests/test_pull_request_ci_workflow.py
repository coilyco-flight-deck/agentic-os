from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_pull_request_ci_workflow_exposes_branch_protection_context() -> None:
    workflow = (ROOT / ".forgejo" / "workflows" / "ci.yml").read_text()
    assert "name: ci" in workflow
    assert "pull_request:" in workflow
    assert "uv run pytest" in workflow


def test_pull_request_ci_builds_dev_base_without_publishing() -> None:
    workflow = (ROOT / ".forgejo" / "workflows" / "ci.yml").read_text()
    assert "build-dev-base:" in workflow
    assert "uses: ./actions/dev-base-build" in workflow
    # PR-only: main gets the same build (plus the publish) through release.yml.
    assert "github.event_name == 'pull_request'" in workflow
    # Build-only contract: the PR job never publishes and never holds creds.
    assert 'push: "true"' not in workflow
    assert "registry_token" not in workflow
    assert "secrets.REGISTRY_TOKEN" not in workflow


def test_pull_request_ci_dry_runs_the_release_tag_computation() -> None:
    workflow = (ROOT / ".forgejo" / "workflows" / "ci.yml").read_text()
    assert "uses: ./actions/tag-bump" in workflow
    assert "create_tag: false" in workflow


def test_pull_request_ci_docs_name_the_required_context() -> None:
    docs = (ROOT / "docs" / "ci-in-dev-base.md").read_text()
    assert "ci / gate" in docs
    assert "ci / build-dev-base" in docs
    assert "pull-requests-and-merge" in docs

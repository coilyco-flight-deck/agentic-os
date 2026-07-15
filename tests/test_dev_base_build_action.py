"""Guard the shared dev-base build/verify action and the PR workflow.

The agentic-os#452 incident was main going red on a publish step no PR ever
exercised. The prevention (agentic-os#454) is one build/verify definition in
actions/dev-base-build that ci.yml runs build-only on pull requests. These
tests pin that PR-side build so it cannot silently drift back apart from the
workflow that validates it.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ACTION = ROOT / "actions" / "dev-base-build" / "action.yml"
CI = ROOT / ".forgejo" / "workflows" / "ci.yml"
RELEASE = ROOT / ".forgejo" / "workflows" / "release.yml"


def test_action_defaults_to_build_only() -> None:
    text = ACTION.read_text(encoding="utf-8")
    assert "push:" in text
    assert 'default: "false"' in text
    assert "scripts/dev-base-build.py" in text


def test_action_guards_every_publish_side_effect_behind_push() -> None:
    text = ACTION.read_text(encoding="utf-8")
    guard = 'if [ "${PUSH}" != "true" ]'
    # Login/builder bootstrap and manifest verify both bail out first on
    # build-only runs.
    assert text.count(guard) == 2
    assert text.index(guard) < text.index("docker login forgejo.coilysiren.me")
    # The build step adds the push flags only inside the push branch.
    assert 'if [ "${PUSH}" = "true" ]' in text
    assert "args+=( --push --platforms" in text


def test_action_bounds_the_build_like_the_old_publish_step() -> None:
    text = ACTION.read_text(encoding="utf-8")
    assert "timeout --preserve-status --kill-after=5m 120m" in text


def test_action_derives_verify_refs_from_the_plan() -> None:
    text = ACTION.read_text(encoding="utf-8")
    assert "plan" in text
    assert '"tiers"' in text
    # The old hand-maintained suffix list is gone from the verify loop.
    assert "for suffix in core lang-node" not in text


def test_ci_uses_the_one_build_definition() -> None:
    release = RELEASE.read_text(encoding="utf-8")
    ci = CI.read_text(encoding="utf-8")
    assert "uses: ./actions/dev-base-build" in ci
    assert "uses: ./actions/publish-dev-base-tier" in release
    # Neither workflow invokes the build helper inline anymore.
    assert "scripts/dev-base-build.py" not in release
    assert "scripts/dev-base-build.py" not in ci


def test_ci_stays_build_only() -> None:
    release = RELEASE.read_text(encoding="utf-8")
    ci = CI.read_text(encoding="utf-8")
    assert 'push: "true"' not in ci
    assert "secrets.REGISTRY_TOKEN" not in ci
    assert "registry-token: ${{ secrets.REGISTRY_TOKEN }}" in release

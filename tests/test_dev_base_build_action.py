"""Guard the shared dev-base build/verify action and its callers.

The agentic-os#452 incident was main going red on a publish step no PR ever
exercised. The prevention (agentic-os#454) is one build/verify definition in
actions/dev-base-build that ci.yml runs build-only on pull requests while the
publish-tier actions keep using the same build script on main. These tests pin
that split so the paths cannot silently drift back apart.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ACTION = ROOT / "actions" / "dev-base-build" / "action.yml"
CI = ROOT / ".forgejo" / "workflows" / "ci.yml"
PROMOTE = ROOT / ".forgejo" / "workflows" / "promote.yml"
PUBLISH_TIER = ROOT / "actions" / "publish-dev-base-tier" / "action.yml"


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


def test_promote_uses_the_tier_action_while_ci_uses_the_build_helper() -> None:
    promote = PROMOTE.read_text(encoding="utf-8")
    ci = CI.read_text(encoding="utf-8")
    assert "uses: ./actions/dev-base-build" in ci
    assert "uses: ./actions/publish-dev-base-tier" in promote
    assert "scripts/dev-base-build.py" in PUBLISH_TIER.read_text(encoding="utf-8")
    # The PR helper stays PR-only.
    assert "uses: ./actions/dev-base-build" not in promote


def test_only_the_promote_workflow_publishes() -> None:
    promote = PROMOTE.read_text(encoding="utf-8")
    ci = CI.read_text(encoding="utf-8")
    assert "registry-token: ${{ secrets.REGISTRY_TOKEN }}" in promote
    assert "registry_token" not in promote
    assert "secrets.REGISTRY_TOKEN" not in ci

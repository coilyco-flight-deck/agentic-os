#!/usr/bin/env python3
"""Tests for check_commit_closes_issue.py."""

import sys

# Add the agentic_os directory to sys.path so we can import our module
sys.path.insert(0, '/workspace/agentic-os')

from agentic_os.check_commit_closes_issue import main


def test_commit_message_accepts_same_repo_url():
    """Test that a commit message with a same-repo Forgejo URL is accepted."""
    # This should pass - using a real forgejo URL for the same repo
    issue = "123"
    commit_msg = (
        "fix: resolve issue with commit validation\n\ncloses "
        f"https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/{issue}"
    )
    assert main(['-'], commit_msg) == 0


def test_commit_message_rejects_cross_repo_url():
    """Test that a commit message with cross-repo Forgejo URL is rejected."""
    # This should fail - url points to different repo
    issue = "123"
    commit_msg = (
        "fix: resolve issue with commit validation\n\ncloses "
        f"https://forgejo.coilysiren.me/coilysiren/other-repo/issues/{issue}"
    )
    assert main(['-'], commit_msg) == 1


def test_commit_message_rejects_bare_short_form():
    """Test that a commit message with bare #N is rejected."""
    # This should fail - using short form
    issue = "123"
    commit_msg = "fix: resolve issue with commit validation\n\ncloses #" + issue
    assert main(['-'], commit_msg) == 1


def test_commit_message_rejects_owner_repo_short_form():
    """Test that a commit message with owner/repo#N is rejected."""
    # This should fail - using short form
    issue = "123"
    commit_msg = (
        "fix: resolve issue with commit validation\n\ncloses "
        + "coilysiren/other-repo#"
        + issue
    )
    assert main(['-'], commit_msg) == 1


def test_commit_message_rejects_no_closing_reference():
    """Test that a commit message with no closing reference is rejected."""
    # This should fail - no closing reference
    commit_msg = "fix: resolve issue with commit validation"
    assert main(['-'], commit_msg) == 1


def test_exempt_commits():
    """Test that exempt commits are accepted."""
    # These should pass as they're exempt from checking
    exempt_commits = [
        "Merge branch 'main'",
        "Revert abc123",
        "fixup! abc123",
        "squash! abc123"
    ]

    for commit_msg in exempt_commits:
        assert main(['-'], commit_msg) == 0


if __name__ == "__main__":
    # Run tests manually
    try:
        test_commit_message_accepts_same_repo_url()
        print("✓ test_commit_message_accepts_same_repo_url passed")

        test_commit_message_rejects_cross_repo_url()
        print("✓ test_commit_message_rejects_cross_repo_url passed")

        test_commit_message_rejects_bare_short_form()
        print("✓ test_commit_message_rejects_bare_short_form passed")

        test_commit_message_rejects_owner_repo_short_form()
        print("✓ test_commit_message_rejects_owner_repo_short_form passed")

        test_commit_message_rejects_no_closing_reference()
        print("✓ test_commit_message_rejects_no_closing_reference passed")

        test_exempt_commits()
        print("✓ test_exempt_commits passed")

        print("\nAll tests passed! ✅")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)

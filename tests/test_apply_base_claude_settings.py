"""Tests for the public-safe Claude Code base settings merge."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "apply-base-claude-settings.py"
SPEC = importlib.util.spec_from_file_location("apply_base_claude_settings", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_base_settings_disable_memory_and_chrome_without_losing_local_denies() -> None:
    settings = {
        "theme": "dark",
        "deniedMcpServers": [{"serverName": "local-browser"}],
    }

    changed = MODULE.merge_base_settings(settings)

    assert settings["autoMemoryEnabled"] is False
    assert settings["theme"] == "dark"
    assert settings["deniedMcpServers"] == [
        {"serverName": "local-browser"},
        {"serverName": "claude-in-chrome"},
    ]
    assert set(changed) == {
        "autoMemoryEnabled",
        "deniedMcpServers",
        "permissions.deny",
        "permissions.allow",
    }
    assert MODULE.merge_base_settings(settings) == []


def test_permission_rules_append_without_touching_sibling_permission_keys() -> None:
    settings = {
        "permissions": {
            "allow": ["Bash(coily:*)"],
            "deny": ["Bash(rm -rf /*)"],
            "defaultMode": "auto",
        },
    }

    MODULE.merge_base_settings(settings)

    permissions = settings["permissions"]
    assert permissions["allow"][0] == "Bash(coily:*)"
    assert permissions["allow"][1:] == MODULE.BASE_ALLOWED_PERMISSIONS
    assert permissions["defaultMode"] == "auto"
    assert permissions["deny"][0] == "Bash(rm -rf /*)"
    assert permissions["deny"][1:] == MODULE.BASE_DENIED_PERMISSIONS
    assert "Bash(kubectl *)" in permissions["deny"]
    assert "Edit(**/.claude/projects/**/memory/**)" in permissions["deny"]


def test_permission_rules_are_created_when_the_key_is_absent() -> None:
    settings: dict = {}

    changed = MODULE.merge_base_settings(settings)

    assert settings["permissions"]["deny"] == MODULE.BASE_DENIED_PERMISSIONS
    assert settings["permissions"]["allow"] == MODULE.BASE_ALLOWED_PERMISSIONS
    assert "permissions.deny" in changed
    assert "permissions.allow" in changed
    assert MODULE.merge_base_settings(settings) == []


def test_retired_permission_rules_are_pruned_from_an_already_converged_host() -> None:
    settings = {
        "permissions": {
            "deny": [
                "Write(**/.claude/projects/**/memory/**)",
                "Edit(**/.claude/projects/**/memory/**)",
                "Bash(rm -rf /*)",
            ],
        },
    }

    changed = MODULE.merge_base_settings(settings)

    deny = settings["permissions"]["deny"]
    assert "Write(**/.claude/projects/**/memory/**)" not in deny
    assert "Edit(**/.claude/projects/**/memory/**)" in deny
    assert "Bash(rm -rf /*)" in deny
    assert "permissions.deny" in changed
    assert MODULE.merge_base_settings(settings) == []


def test_no_retired_rule_is_also_a_live_rule() -> None:
    assert not set(MODULE.RETIRED_DENIED_PERMISSIONS) & set(MODULE.BASE_DENIED_PERMISSIONS)

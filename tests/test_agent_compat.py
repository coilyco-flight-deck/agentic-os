"""Tests for scripts/agent-compat.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "agent-compat.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("agent_compat", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_harness_filter_builds_selected_suite_only() -> None:
    script = _load_script()

    suite = script.build_suite(["codex"])
    tests = list(suite)

    assert tests
    assert {test.__class__.__name__ for test in tests} == {"CodexCompat"}


def test_ollama_env_prefers_existing_environment(monkeypatch, tmp_path: Path) -> None:
    script = _load_script()
    config = tmp_path / "config.yaml"
    config.write_text("OLLAMA_HOST: configured\nGOOSE_MODEL: configured-model\n", encoding="utf-8")
    monkeypatch.setattr(script, "GOOSE_CONFIG", config)
    monkeypatch.setenv("OLLAMA_HOST", "env-host")
    monkeypatch.delenv("GOOSE_MODEL", raising=False)

    env = script.ollama_env()

    assert env == {"OLLAMA_HOST": "env-host", "GOOSE_MODEL": "configured-model"}
    # goose_env stays a back-compat alias for the same reader.
    assert script.goose_env is script.ollama_env


def test_list_prints_harness_names(capsys) -> None:
    script = _load_script()

    assert script.main(["--list"]) == 0

    out = capsys.readouterr().out.splitlines()
    assert "codex" in out
    assert "opencode" in out


def test_roster_matches_ward_embedded_roster() -> None:
    """The probe roster must equal `ward agents list --json` - the drift pin.

    aos is the consumer of ward's embedded fleet roster (aos#310 issue 5). If
    ward adds, removes, or renames an agent, this test fails until the probe set
    in scripts/agent-compat.py conforms. Skips when the ward binary is absent or
    predates the `agents list --json` surface (ward#417), so it validates on a
    current host but does not fail an old one.
    """
    script = _load_script()
    try:
        ward_names = script.ward_roster_names()
    except script.WardRosterUnavailable as exc:
        pytest.skip(f"ward roster surface unavailable: {exc}")

    assert set(script.HARNESS_CASES) == set(ward_names), (
        "agent-compat probe roster drifted from ward's embedded fleet roster; "
        f"probes={sorted(script.HARNESS_CASES)} ward={sorted(ward_names)}"
    )


def test_resolve_default_roster_falls_back_when_ward_unavailable(monkeypatch, capsys) -> None:
    script = _load_script()

    def _boom() -> list[str]:
        raise script.WardRosterUnavailable("ward is not on PATH")

    monkeypatch.setattr(script, "ward_roster_names", _boom)

    assert script.resolve_default_roster() == sorted(script.HARNESS_CASES)
    assert "ward roster unavailable" in capsys.readouterr().err


def test_resolve_default_roster_uses_ward_names_and_flags_gaps(monkeypatch, capsys) -> None:
    script = _load_script()
    # ward reports a not-yet-probed agent alongside known ones.
    monkeypatch.setattr(script, "ward_roster_names", lambda: ["claude", "codex", "newharness"])

    roster = script.resolve_default_roster()

    assert roster == ["claude", "codex"]
    assert "newharness" in capsys.readouterr().err

"""Tests for scripts/agent-compat.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path


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


def test_goose_env_prefers_existing_environment(monkeypatch, tmp_path: Path) -> None:
    script = _load_script()
    config = tmp_path / "config.yaml"
    config.write_text("OLLAMA_HOST: configured\nGOOSE_MODEL: configured-model\n", encoding="utf-8")
    monkeypatch.setattr(script, "GOOSE_CONFIG", config)
    monkeypatch.setenv("OLLAMA_HOST", "env-host")
    monkeypatch.delenv("GOOSE_MODEL", raising=False)

    env = script.goose_env()

    assert env == {"OLLAMA_HOST": "env-host", "GOOSE_MODEL": "configured-model"}


def test_list_prints_harness_names(capsys) -> None:
    script = _load_script()

    assert script.main(["--list"]) == 0

    out = capsys.readouterr().out.splitlines()
    assert "codex" in out
    assert "qwen" in out

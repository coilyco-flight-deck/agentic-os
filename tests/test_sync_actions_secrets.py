"""Tests for the Actions-secret source manifest loader."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "sync-actions-secrets.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("sync_actions_secrets", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_action_defaults_manifest_is_valid() -> None:
    mod = _load_script()
    sources = mod.load_secret_sources(mod.TELEGRAM_DEFAULTS_PATH)
    assert sources
    assert sources.items() <= mod.MAPPING["agentic-os"].items()


def test_manifest_loader_rejects_missing_parameter_path(tmp_path) -> None:
    mod = _load_script()
    manifest = tmp_path / "defaults.json"
    manifest.write_text(
        json.dumps(
            {
                "schema-version": 1,
                "secrets": {
                    "token": {
                        "actions-secret": "TOKEN",
                        "ssm-parameter": "not-an-absolute-path",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="invalid action secret sources"):
        mod.load_secret_sources(manifest)


def test_admin_token_requires_attended_environment(monkeypatch) -> None:
    mod = _load_script()
    monkeypatch.delenv("FORGEJO_ADMIN_TOKEN", raising=False)

    with pytest.raises(SystemExit, match="FORGEJO_ADMIN_TOKEN is required"):
        mod.admin_token()


def test_admin_token_reads_attended_environment(monkeypatch) -> None:
    mod = _load_script()
    monkeypatch.setenv("FORGEJO_ADMIN_TOKEN", " fixture-token ")

    assert mod.admin_token() == "fixture-token"

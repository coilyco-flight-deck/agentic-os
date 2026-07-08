"""Tests for scripts.audit_pre_commit_coverage manual-hook filtering."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "audit-pre-commit-coverage.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("audit_pre_commit_coverage", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_expected_hook_ids_skips_manual_only_hooks(monkeypatch, tmp_path: Path) -> None:
    hooks = tmp_path / ".pre-commit-hooks.yaml"
    hooks.write_text(
        """
- id: active-hook
  name: active
- id: manual-hook
  name: manual
  stages: [manual]
- id: mixed-hook
  name: mixed
  stages: [manual, pre-commit]
""",
        encoding="utf-8",
    )
    audit = _load_script()
    monkeypatch.setattr(audit, "HOOKS_FILE", hooks, raising=True)
    assert audit.expected_hook_ids() == ["active-hook", "mixed-hook"]

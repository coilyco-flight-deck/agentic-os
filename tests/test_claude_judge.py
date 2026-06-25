"""Tests for claude_judge: the Claude-CLI judge over the goose-json contract
(coilyco-flight-deck/agentic-os#271).

The live `claude` call is not exercised here (the same way goose_json's live
Goose call is not); these lock the parsing - result-envelope extraction, JSON
recovery from a fenced or prose-wrapped reply, schema validation - and the
dict|None fail-soft the triage command engine depends on.
"""
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import claude_judge as cj  # noqa: E402

SCHEMA = {"type": "object", "required": ["score"], "properties": {"score": {"type": "integer"}}}


@pytest.mark.parametrize("text,want", [
    ('{"score": 5}', {"score": 5}),
    ('```json\n{"score": 5}\n```', {"score": 5}),
    ('```\n{"score": 5}\n```', {"score": 5}),
    ('Here is my answer: {"score": 5} - done.', {"score": 5}),
    ("not json", None),
    ("", None),
])
def test_extract_json(text, want):
    assert cj._extract_json(text) == want


def test_claude_result_pulls_result_field():
    env = json.dumps({"type": "result", "result": '{"score": 9}', "session_id": "x"})
    assert cj._claude_result(env) == '{"score": 9}'


def test_claude_result_handles_bad_envelope_and_missing_field():
    assert cj._claude_result("not json") is None
    assert cj._claude_result('{"type": "result"}') is None


def _fake_claude(stdout, returncode=0):
    def run(cmd, capture_output=True, text=True, timeout=120):
        run.cmd = cmd
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")
    return run


def test_judge_returns_validated_object(monkeypatch):
    env = json.dumps({"type": "result", "result": '{"score": 88}'})
    fake = _fake_claude(env)
    monkeypatch.setattr(cj.subprocess, "run", fake)
    assert cj.judge("rank it", SCHEMA, model="opus") == {"score": 88}
    # The prompt and model reach the claude CLI in print/json mode.
    assert fake.cmd[:2] == ["claude", "-p"]
    assert "--output-format" in fake.cmd and "json" in fake.cmd
    assert fake.cmd[fake.cmd.index("--model") + 1] == "opus"
    assert "rank it" in fake.cmd[2]  # prompt embedded


def test_judge_rejects_schema_mismatch(monkeypatch):
    env = json.dumps({"type": "result", "result": '{"nope": 1}'})
    monkeypatch.setattr(cj.subprocess, "run", _fake_claude(env))
    assert cj.judge("p", SCHEMA) is None


def test_judge_handles_nonzero_exit(monkeypatch):
    monkeypatch.setattr(cj.subprocess, "run", _fake_claude("", returncode=2))
    assert cj.judge("p", SCHEMA) is None


def test_judge_swallows_subprocess_error(monkeypatch):
    def boom(*a, **k):
        raise OSError("claude not found")
    monkeypatch.setattr(cj.subprocess, "run", boom)
    assert cj.judge("p", SCHEMA) is None


def test_cli_contract_prints_clean_json(monkeypatch, tmp_path, capsys):
    schema_file = tmp_path / "s.json"
    schema_file.write_text(json.dumps(SCHEMA))
    prompt_file = tmp_path / "p.txt"
    prompt_file.write_text("score this")
    env = json.dumps({"type": "result", "result": '{"score": 3}'})
    monkeypatch.setattr(cj.subprocess, "run", _fake_claude(env))
    rc = cj.main(["--schema", str(schema_file), "--prompt-file", str(prompt_file)])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"score": 3}


def test_cli_contract_nonzero_on_failure(monkeypatch, tmp_path):
    schema_file = tmp_path / "s.json"
    schema_file.write_text(json.dumps(SCHEMA))
    monkeypatch.setattr(cj.subprocess, "run", _fake_claude("", returncode=1))
    assert cj.main(["--schema", str(schema_file), "--text", "x"]) == 1

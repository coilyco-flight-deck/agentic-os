"""Tests for the pluggable judgment engine seam (coilyco-flight-deck/agentic-os#271).

goose-triage routes every judgment through one swappable `ask` seam. These lock
the engine registry (goose-json default, command, claude), the command engine's
goose-json CLI contract and dict|None fail-soft, and that the selected engine's
attribution reaches goose-triage's report line and comment footer.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import triage_engines as te  # noqa: E402

_spec = importlib.util.spec_from_file_location("goose_triage", SCRIPTS / "goose-triage.py")
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)

SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["score"], "properties": {"score": {"type": "integer"}}}


def test_default_engine_is_goose_json():
    e = te.select_engine("goose-json")
    assert e.name == "goose-json"
    assert e.attribution == te.DEFAULT_ATTRIBUTION
    # The default engine's ask is exactly goose_json.ask - the unchanged path.
    import goose_json
    assert e.ask is goose_json.ask


def test_claude_engine_is_command_over_the_bundled_judge():
    e = te.select_engine("claude")
    assert e.name == "claude" and "Claude" in e.attribution


def test_command_engine_requires_a_command():
    with pytest.raises(ValueError, match="engine-cmd"):
        te.select_engine("command")


def test_unknown_engine_raises():
    with pytest.raises(ValueError, match="unknown engine"):
        te.select_engine("bogus")


def test_command_engine_runs_contract_and_returns_object(monkeypatch):
    cap = {}

    def fake_run(cmd, capture_output=True, text=True, timeout=120):
        cap["cmd"] = cmd
        # The judge is handed the schema and prompt as files, goose-json contract.
        i = cmd.index("--schema")
        cap["schema"] = json.loads(Path(cmd[i + 1]).read_text())
        j = cmd.index("--prompt-file")
        cap["prompt"] = Path(cmd[j + 1]).read_text()
        return types.SimpleNamespace(returncode=0, stdout='{"score": 7}', stderr="")

    monkeypatch.setattr(te.subprocess, "run", fake_run)
    e = te.select_engine("command", cmd="my-judge --model x", attribution="My Judge")
    out = e.ask("rank this", SCHEMA, repo="o/r", label="urgency")
    assert out == {"score": 7}
    assert cap["cmd"][:3] == ["my-judge", "--model", "x"]
    assert cap["schema"] == SCHEMA and cap["prompt"] == "rank this"
    assert e.attribution == "My Judge"


def test_command_engine_attribution_defaults_to_the_command(monkeypatch):
    e = te.select_engine("command", cmd="weird-judge --flag")
    assert e.attribution == "weird-judge --flag"


@pytest.mark.parametrize("ret,stdout", [
    (1, '{"score": 7}'),      # non-zero exit -> failed judgment
    (0, "not json at all"),   # unparseable stdout
    (0, '{"nope": 1}'),       # parses but misses a required key
    (0, ""),                  # empty stdout
])
def test_command_engine_fails_soft_to_none(monkeypatch, ret, stdout):
    monkeypatch.setattr(te.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(returncode=ret, stdout=stdout, stderr=""))
    e = te.select_engine("command", cmd="judge")
    assert e.ask("p", SCHEMA) is None


def test_command_engine_swallows_subprocess_failure(monkeypatch):
    def boom(*a, **k):
        raise OSError("no such command")
    monkeypatch.setattr(te.subprocess, "run", boom)
    e = te.select_engine("command", cmd="missing-judge")
    assert e.ask("p", SCHEMA) is None


def test_env_fallback_selects_engine(monkeypatch):
    monkeypatch.setenv("AOS_TRIAGE_ENGINE", "claude")
    assert te.select_engine_from_env().name == "claude"
    monkeypatch.setenv("AOS_TRIAGE_ENGINE", "command")
    monkeypatch.setenv("AOS_TRIAGE_ENGINE_CMD", "judge")
    monkeypatch.setenv("AOS_TRIAGE_ENGINE_ATTRIBUTION", "Env Judge")
    e = te.select_engine_from_env()
    assert e.name == "command" and e.attribution == "Env Judge"


def test_explicit_arg_beats_env(monkeypatch):
    monkeypatch.setenv("AOS_TRIAGE_ENGINE", "claude")
    assert te.select_engine_from_env("goose-json").name == "goose-json"


# --- attribution threads into goose-triage's report + comment footer ---

def test_report_names_the_active_engine():
    result = {"repo": "o/r", "n": 1, "capped": False, "attribution": "Custom Judge",
              "tiers": {t: [] for t in ("P0", "P1", "P2", "P3", "P4")},
              "issues": [], "goose_failures": {}, "applied": None}
    md, _yaml = gt.write_report(result)
    text = Path(md).read_text()
    assert "triaged by Custom Judge" in text
    assert "Goose (qwen3-coder:30b)" not in text


def test_comment_footer_names_the_active_engine(monkeypatch):
    monkeypatch.setattr(gt, "ATTRIBUTION", "Custom Judge")
    body = gt.render_comment({"num": 1, "title": "t", "tier": "P2", "mode": "headless"}, "2026-06-25")
    assert "judge: Custom Judge" in body
    assert "qwen3-coder:30b" not in body

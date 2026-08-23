"""Tests for the generic voice-guide linter engine.

The engine shipped from AOS with Kai's pronouns, private address, and prose
conventions compiled into it, so a public reusable engine owned personal
runtime configuration. Rules now come from a profile. See agentic-os#830.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / ".agents" / "composed" / "writing-voice-guide-linter" / "lint.py"
EXAMPLE = ROOT / "tests" / "fixtures" / "voice-profile-example.json"


def _engine():
    spec = importlib.util.spec_from_file_location("voice_lint", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _profile(tmp_path: Path, rules: list) -> Path:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"name": "t", "rules": rules}), encoding="utf-8")
    return path


def test_the_engine_carries_no_house_style() -> None:
    # The acceptance criterion, asserted against the file rather than trusted.
    source = ENGINE.read_text(encoding="utf-8")

    for personal in ("Kai", "she/her", "coilysiren", "gmail", "em-dash", "—"):
        assert personal not in source, personal


def test_a_fixture_profile_lints_without_any_kai_policy(tmp_path: Path) -> None:
    engine = _engine()
    target = tmp_path / "prose.md"
    target.write_text("Maybe this — works\n", encoding="utf-8")

    findings = engine.lint_file(target, engine.load_profile(EXAMPLE))

    assert {found[2] for found in findings} == {"em-dash", "hedge"}


def test_a_line_rule_reports_once_and_suppresses_span_rules(tmp_path: Path) -> None:
    # A table row is punctuation-dense, so reporting it per span rule buries it.
    engine = _engine()
    target = tmp_path / "prose.md"
    target.write_text("| maybe | maybe |\n", encoding="utf-8")

    findings = engine.lint_file(target, engine.load_profile(EXAMPLE))

    assert len(findings) == 1
    assert findings[0][2] == "prose-table"


def test_fenced_code_is_not_prose(tmp_path: Path) -> None:
    engine = _engine()
    target = tmp_path / "prose.md"
    target.write_text("```\nmaybe —\n```\nmaybe\n", encoding="utf-8")

    findings = engine.lint_file(target, engine.load_profile(EXAMPLE))

    assert [found[1] for found in findings] == [4]


def test_flags_are_honoured(tmp_path: Path) -> None:
    engine = _engine()
    profile = _profile(tmp_path, [{"id": "x", "pattern": "abc", "hint": "h", "flags": ["i"]}])
    target = tmp_path / "prose.md"
    target.write_text("ABC\n", encoding="utf-8")

    assert len(engine.lint_file(target, engine.load_profile(profile))) == 1


@pytest.mark.parametrize(
    ("rules", "expected"),
    [
        ([], "no rules"),
        ([{"id": "", "pattern": "a", "hint": "h"}], "id is a non-empty string"),
        ([{"id": "a", "hint": "h"}], "pattern is a non-empty string"),
        ([{"id": "a", "pattern": "a"}], "hint is a non-empty string"),
        ([{"id": "a", "pattern": "a", "hint": "h", "scope": "word"}], "scope is"),
        ([{"id": "a", "pattern": "a", "hint": "h", "flags": ["q"]}], "unknown flag"),
        ([{"id": "a", "pattern": "([", "hint": "h"}], "unterminated"),
    ],
)
def test_a_profile_that_cannot_be_trusted_is_an_error(
    tmp_path: Path, rules: list, expected: str
) -> None:
    # Never zero rules: linting nothing and reporting success is the failure.
    engine = _engine()

    with pytest.raises(engine.ProfileError) as raised:
        engine.load_profile(_profile(tmp_path, rules))

    assert expected in str(raised.value)


def test_a_missing_profile_is_an_error(tmp_path: Path) -> None:
    engine = _engine()

    with pytest.raises(engine.ProfileError):
        engine.load_profile(tmp_path / "absent.json")


def test_strict_decides_the_exit_status(tmp_path: Path, capsys) -> None:
    engine = _engine()
    target = tmp_path / "prose.md"
    target.write_text("maybe\n", encoding="utf-8")
    args = ["--profile", str(EXAMPLE), str(target)]

    assert engine.main(args) == 0
    assert engine.main([*args, "--strict"]) == 1
    assert "[hedge]" in capsys.readouterr().out


def test_no_profile_is_a_usage_error(tmp_path: Path) -> None:
    engine = _engine()

    assert engine.main([str(tmp_path)]) == 2
    assert engine.main(["--profile"]) == 2

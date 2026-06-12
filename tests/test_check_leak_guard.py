"""Tests for agentic_os.pre_commit.check_leak_guard: the encoded-leak guard.

Covers the three rule shapes (scope-all, repo-scoped, cycle-break) plus the
mechanics that make them safe: hex terms decoded only in memory, word-boundary
matching, only_globs / allow_globs, and that a violation never echoes the term.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from agentic_os.pre_commit import check_leak_guard as lg


def _hex(term: str) -> str:
    return term.encode("utf-8").hex()


def _rule(**over) -> dict:
    base = {"id": "r", "term_hex": _hex("needle"), "message": "fix it"}
    base.update(over)
    return base


# --- pure matching logic (no git, no fs) ------------------------------------

def test_compile_decodes_hex_and_word_boundary() -> None:
    matcher = lg._compile(_rule())
    assert matcher.search("a needle in here")
    assert not matcher.search("needles and threads")  # boundary: no match in-word


def test_compile_word_boundary_off_matches_substring() -> None:
    matcher = lg._compile(_rule(word_boundary=False))
    assert matcher.search("needles")


def test_compile_case_insensitive_by_default() -> None:
    assert lg._compile(_rule()).search("A NEEDLE")
    assert not lg._compile(_rule(case_sensitive=True)).search("A NEEDLE")


def test_compile_bad_hex_is_skipped_not_raised() -> None:
    assert lg._compile(_rule(term_hex="zzzz")) is None


def test_scan_reports_id_and_message_never_the_term() -> None:
    rule = _rule(id="employer", message="resolve at run time")
    hits = lg.scan("f.md", "the needle line\nclean line\n", rule, lg._compile(rule))
    assert hits == ["f.md:1: leak-guard[employer] - resolve at run time"]
    assert "needle" not in hits[0]  # the guard's own output is not a leak


def test_rule_applies_scope() -> None:
    assert lg._rule_applies(_rule(repos=None), "anything")
    assert lg._rule_applies(_rule(repos=["cli-guard"]), "cli-guard")
    assert not lg._rule_applies(_rule(repos=["cli-guard"]), "agentic-os")


# --- end-to-end through main() in a throwaway repo --------------------------

def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(tmp_path: Path, remote: str = "agentic-os") -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "remote", "add", "origin",
         f"https://forgejo.coilysiren.me/coilyco-flight-deck/{remote}.git")
    return tmp_path


def _run(monkeypatch, tmp_path: Path, rules: list[dict]) -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lg, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lg, "RULES", rules)
    return lg.main()


def test_only_globs_enforces_front_page_alone(monkeypatch, tmp_path, capsys) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("names the needle\n")
    (repo / "tooling.py").write_text("needle is fine in tooling\n")
    _git(repo, "add", "-A")
    rule = _rule(repos=["agentic-os"], only_globs=["README.md"])
    assert _run(monkeypatch, repo, [rule]) == 1
    err = capsys.readouterr().err
    assert "README.md" in err and "tooling.py" not in err  # only the front page


def test_allow_globs_exempts_bio_surface(monkeypatch, tmp_path, capsys) -> None:
    repo = _repo(tmp_path)
    (repo / "resume.md").write_text("needle the employer\n")
    (repo / "config.toml").write_text("needle hardcoded\n")
    _git(repo, "add", "-A")
    rule = _rule(allow_globs=["resume.md"])
    assert _run(monkeypatch, repo, [rule]) == 1
    err = capsys.readouterr().err
    assert "config.toml" in err and "resume.md" not in err  # bio exempt


def test_out_of_scope_repo_passes(monkeypatch, tmp_path) -> None:
    repo = _repo(tmp_path, remote="agentic-os")
    (repo / "f.md").write_text("needle everywhere\n")
    _git(repo, "add", "-A")
    rule = _rule(repos=["cli-guard"])  # not this repo
    assert _run(monkeypatch, repo, [rule]) == 0

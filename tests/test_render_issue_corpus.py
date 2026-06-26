"""Tests for render-issue-corpus: the git-mirrored issue-corpus discovery index.

Cover the pure render/slug/manifest logic, the ward-kdl Forgejo I/O command
construction (all reads route through `ward ops forgejo`, so the script holds no
FORGEJO_TOKEN - agentic-os#297, #267), the incremental skip/relocate behavior, and
the trufflehog privacy backstop's fail-closed contract. Forgejo and trufflehog
calls mock to subprocess, so no network and no scanner binary are needed.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("render_issue_corpus",
                                               SCRIPTS / "render-issue-corpus.py")
ric = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ric)


def _fake_run(captured, *, returncode=0, stdout="", stderr=""):
    """A subprocess.run stand-in that records argv and returns a fixed result."""
    def run(cmd, capture_output=True, text=True, timeout=120):
        captured.append(cmd)
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return run


def _issue(num, *, title="A bug", state="open", updated="2026-01-01T00:00:00Z",
           body="body text", comments=0, labels=None, user="kai", pr=False):
    d = {"number": num, "title": title, "state": state, "updated_at": updated,
         "body": body, "comments": comments, "labels": labels or [],
         "user": {"login": user}, "html_url": f"https://h/{num}"}
    if pr:
        d["pull_request"] = {"url": "x"}
    return d


def test_split_repo_ok():
    assert ric._split_repo("coilysiren/inbox") == ("coilysiren", "inbox")


@pytest.mark.parametrize("bad", ["inbox", "", "/inbox", "owner/"])
def test_split_repo_rejects_non_slug(bad):
    with pytest.raises(ValueError):
        ric._split_repo(bad)


@pytest.mark.parametrize("title,expected", [
    ("Fix the Thing", "fix-the-thing"),
    ("  Trailing/Slashes!! ", "trailing-slashes"),
    ("***", "untitled"),
    ("", "untitled"),
])
def test_slugify(title, expected):
    assert ric.slugify(title) == expected


def test_slugify_caps_length_without_trailing_hyphen():
    slug = ric.slugify("word " * 40)
    assert len(slug) <= ric.SLUG_MAX
    assert not slug.endswith("-")


def test_issue_relpath():
    assert ric.issue_relpath("coilysiren/inbox", _issue(7, title="Hi There")) \
        == "coilysiren/inbox/7-hi-there.md"


def test_load_repos_skips_comments_and_blanks(tmp_path):
    f = tmp_path / "repos.txt"
    f.write_text("# header\n\ncoilysiren/inbox\n  coilyco-flight-deck/ward \n")
    assert ric.load_repos(f) == ["coilysiren/inbox", "coilyco-flight-deck/ward"]


def test_load_repos_rejects_malformed_entry(tmp_path):
    f = tmp_path / "repos.txt"
    f.write_text("not-a-slug\n")
    with pytest.raises(ValueError):
        ric.load_repos(f)


def test_label_names_pulls_name_from_objects():
    issue = _issue(1, labels=[{"name": "P1"}, {"name": "headless"}, {}])
    assert ric._label_names(issue) == ["P1", "headless"]


def test_user_login_falls_back():
    assert ric._user_login({"user": None, "original_author": "ext"}) == "ext"
    assert ric._user_login({}) == "unknown"


def test_render_markdown_has_header_disclaimer_and_thread():
    issue = _issue(297, title="Corpus", state="closed",
                   updated="2026-06-26T02:41:17Z", body="the body",
                   comments=1, labels=[{"name": "P2"}], user="coilysiren")
    comments = [{"user": {"login": "kai"}, "created_at": "2026-06-26T03:00:00Z",
                 "body": "a reply"}]
    md = ric.render_markdown("coilysiren/inbox", issue, comments, "2026-06-26T04:00:00Z")
    assert "ward ops forgejo issue view coilysiren inbox 297" in md
    assert "Discovery index, not source of truth" in md
    assert "- **state:** closed" in md
    assert "- **labels:** P2" in md
    assert "- **source-updated-at:** 2026-06-26T02:41:17Z" in md
    assert "- **rendered-at:** 2026-06-26T04:00:00Z" in md
    assert "the body" in md
    assert "### Comment 1 - kai - 2026-06-26T03:00:00Z" in md
    assert "a reply" in md


def test_render_markdown_empty_body_and_no_comments():
    md = ric.render_markdown("o/r", _issue(1, body="", comments=0), [], "T")
    assert "_(empty)_" in md
    assert "_(no comments)_" in md


def test_fj_appends_json_for_reads_and_parses(monkeypatch):
    cap = []
    monkeypatch.setattr(ric.subprocess, "run", _fake_run(cap, stdout='[{"number":1}]'))
    assert ric._fj(["issue", "list-all", "o", "r"]) == [{"number": 1}]
    assert cap[0] == [ric.WARD, "ops", "forgejo", "issue", "list-all", "o", "r",
                      "--output", "json"]


def test_fj_nonzero_raises_with_stderr(monkeypatch):
    monkeypatch.setattr(ric.subprocess, "run",
                        _fake_run([], returncode=1, stderr="denied by policy"))
    with pytest.raises(ric.WardForgejoError, match="denied by policy"):
        ric._fj(["issue", "list-all", "o", "r"])


def test_list_issues_state_all_type_issues_and_drops_prs(monkeypatch):
    cap = []
    payload = '[{"number":1,"pull_request":null},{"number":2,"pull_request":{"url":"x"}}]'

    def run(cmd, capture_output=True, text=True, timeout=120):
        cap.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout=payload, stderr="")
    monkeypatch.setattr(ric.subprocess, "run", run)
    issues = ric.list_issues("o/r")
    assert [i["number"] for i in issues] == [1]
    assert "--state" in cap[0] and "all" in cap[0]
    assert "--type" in cap[0] and "issues" in cap[0]


def test_manifest_roundtrip(tmp_path):
    ric.save_manifest(tmp_path, {"o/r#1": {"updated_at": "T"}})
    assert ric.load_manifest(tmp_path) == {"o/r#1": {"updated_at": "T"}}


def test_load_manifest_missing_and_corrupt(tmp_path):
    assert ric.load_manifest(tmp_path) == {}
    (tmp_path / ric.MANIFEST_NAME).write_text("{not json")
    assert ric.load_manifest(tmp_path) == {}


def test_render_repo_writes_skips_and_relocates(tmp_path, monkeypatch):
    issue = _issue(5, title="First", updated="2026-01-01T00:00:00Z")
    monkeypatch.setattr(ric, "list_issues", lambda repo, since=None: [issue])
    monkeypatch.setattr(ric, "list_comments", lambda repo, num: [])
    manifest = {}

    c1 = ric.render_repo("o/r", tmp_path, manifest, "T1", force=False)
    assert c1 == {"rendered": 1, "skipped": 0, "removed": 0}
    assert (tmp_path / "o/r/5-first.md").exists()
    assert manifest["o/r#5"]["updated_at"] == "2026-01-01T00:00:00Z"

    # unchanged updated_at -> skipped, no comment fetch needed
    c2 = ric.render_repo("o/r", tmp_path, manifest, "T2", force=False)
    assert c2 == {"rendered": 0, "skipped": 1, "removed": 0}

    # title edit bumps updated_at and moves the path; the stale file is removed
    issue["title"] = "Renamed"
    issue["updated_at"] = "2026-02-02T00:00:00Z"
    c3 = ric.render_repo("o/r", tmp_path, manifest, "T3", force=False)
    assert c3 == {"rendered": 1, "skipped": 0, "removed": 1}
    assert (tmp_path / "o/r/5-renamed.md").exists()
    assert not (tmp_path / "o/r/5-first.md").exists()


def test_render_repo_force_rerenders(tmp_path, monkeypatch):
    issue = _issue(5, updated="2026-01-01T00:00:00Z")
    monkeypatch.setattr(ric, "list_issues", lambda repo, since=None: [issue])
    monkeypatch.setattr(ric, "list_comments", lambda repo, num: [])
    manifest = {}
    ric.render_repo("o/r", tmp_path, manifest, "T1", force=False)
    c = ric.render_repo("o/r", tmp_path, manifest, "T2", force=True)
    assert c["rendered"] == 1 and c["skipped"] == 0


def test_render_repo_fetches_comments_only_when_present(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ric, "list_issues", lambda repo, since=None: [
        _issue(1, comments=0), _issue(2, comments=3)])
    monkeypatch.setattr(ric, "list_comments",
                        lambda repo, num: calls.append(num) or [])
    ric.render_repo("o/r", tmp_path, {}, "T", force=False)
    assert calls == [2]


def test_run_trufflehog_missing_binary_fails_closed(monkeypatch, tmp_path):
    def run(cmd, capture_output=True, text=True, timeout=600):
        raise FileNotFoundError("trufflehog")
    monkeypatch.setattr(ric.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="not on PATH"):
        ric.run_trufflehog(tmp_path)


def test_run_trufflehog_finding_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(ric.subprocess, "run",
                        _fake_run([], returncode=183, stdout="found a key"))
    with pytest.raises(RuntimeError, match="flagged a secret"):
        ric.run_trufflehog(tmp_path)


def test_run_trufflehog_clean_passes(monkeypatch, tmp_path):
    monkeypatch.setattr(ric.subprocess, "run", _fake_run([], returncode=0))
    ric.run_trufflehog(tmp_path)  # no raise


def test_main_rejects_non_directory(tmp_path):
    with pytest.raises(SystemExit):
        ric.main(["--mirror-dir", str(tmp_path / "nope")])

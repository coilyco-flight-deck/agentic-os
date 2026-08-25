"""Tests for agentic_os.pre_commit.check_outbound_links: outbound link hygiene."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_os import config
from agentic_os.pre_commit import check_outbound_links as col


def _write(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _run(monkeypatch: pytest.MonkeyPatch, root: Path) -> int:
    monkeypatch.setattr(col, "REPO_ROOT", root)
    monkeypatch.setattr(config, "REPO_ROOT", root)
    config.reset_build_output_cache()
    return col.main(["check-outbound-links"])


def _err(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().err


def test_clean_repo_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(
        tmp_path,
        "README.md",
        "See [umbra](https://github.com/coilyco-flight-deck/umbra).\n",
    )
    assert _run(monkeypatch, tmp_path) == 0


def test_retired_repository_name_is_caught_with_its_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        tmp_path,
        "README.md",
        "See [cli-guard](https://github.com/coilyco-flight-deck/cli-guard).\n",
    )
    assert _run(monkeypatch, tmp_path) == 1
    err = _err(capsys)
    assert "retired-name" in err
    assert "use 'umbra'" in err


def test_retired_display_name_is_case_sensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "docs/a.md", "The Ward MCP runtime.\n")
    _write(tmp_path, "docs/b.md", "ward mcp brokering is ordinary prose.\n")
    assert _run(monkeypatch, tmp_path) == 1
    err = _err(capsys)
    assert "docs/a.md" in err.replace("\\", "/")
    assert "docs/b.md" not in err.replace("\\", "/")


def test_backticked_retired_name_is_a_mention_not_a_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "docs/rename.md", "`cli-guard` was renamed to `umbra`.\n")
    assert _run(monkeypatch, tmp_path) == 0


def test_fenced_retired_name_is_exempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "docs/rename.md", "```\ncli-guard\n```\n")
    assert _run(monkeypatch, tmp_path) == 0


def test_retired_path_is_caught_in_an_html_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        tmp_path,
        "README.md",
        '<a href="https://coilysiren.me/orgs/coilyco-bridge/">Organization profile</a>\n',
    )
    assert _run(monkeypatch, tmp_path) == 1
    assert "retired-path" in _err(capsys)


def test_canonical_host_is_off_until_the_repo_declares_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "README.md",
        "[umbra](https://forgejo.coilysiren.me/coilyco-flight-deck/umbra)\n",
    )
    assert _run(monkeypatch, tmp_path) == 0


def test_canonical_host_fires_once_declared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        '[tool.agentic-os.outbound-link-hygiene]\ncanonical_repo_host = "github.com"\n',
    )
    _write(
        tmp_path,
        "README.md",
        "[umbra](https://forgejo.coilysiren.me/coilyco-flight-deck/umbra)\n",
    )
    assert _run(monkeypatch, tmp_path) == 1
    err = _err(capsys)
    assert "canonical-host" in err
    assert "github.com" in err


def test_text_target_mismatch_needs_a_slug_the_tree_knows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        tmp_path,
        "docs/a.md",
        "[galaxy-gen](https://github.com/coilysiren/galaxy-gen)\n",
    )
    _write(
        tmp_path,
        "docs/b.md",
        "[galaxy-gen](https://github.com/coilysiren/website)\n",
    )
    assert _run(monkeypatch, tmp_path) == 1
    err = _err(capsys)
    assert "text-target-mismatch" in err
    assert "coilysiren/website" in err


def test_unknown_label_on_a_repo_link_is_not_a_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "README.md",
        "[tap](https://github.com/coilyco-flight-deck/homebrew-tap)\n",
    )
    assert _run(monkeypatch, tmp_path) == 0


def test_deep_link_label_is_not_a_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "README.md",
        "[umbra](https://github.com/coilyco-flight-deck/umbra)\n"
        "[docs](https://github.com/coilyco-flight-deck/umbra/blob/main/README.md)\n",
    )
    assert _run(monkeypatch, tmp_path) == 0


def test_placeholder_and_empty_targets_are_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "README.md", "[a]() [b](#) [c](TODO)\n")
    assert _run(monkeypatch, tmp_path) == 1
    assert _err(capsys).count("placeholder-target") == 3


def test_local_host_in_prose_is_caught_but_not_in_a_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "docs/a.md", "Open http://localhost:8080/ to see it.\n")
    _write(tmp_path, "docs/b.md", "```\ncurl http://localhost:8080/\n```\n")
    assert _run(monkeypatch, tmp_path) == 1
    err = _err(capsys).replace("\\", "/")
    assert "placeholder-url" in err
    assert "docs/b.md" not in err


def test_excludes_opt_a_path_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        '[tool.agentic-os.outbound-link-hygiene]\nexcludes = ["data/digests/**"]\n',
    )
    _write(tmp_path, "data/digests/x.md", "cli-guard lives here.\n")
    assert _run(monkeypatch, tmp_path) == 0


def test_enabled_false_disables_the_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        "[tool.agentic-os.outbound-link-hygiene]\nenabled = false\n",
    )
    _write(tmp_path, "README.md", "cli-guard\n")
    assert _run(monkeypatch, tmp_path) == 0


def test_autolink_and_bare_url_are_both_extracted() -> None:
    text = "<https://example.com/a> and https://example.com/b, trailing.\n"
    urls = {ref.url for ref in col.extract_references(text)}
    assert urls == {"https://example.com/a", "https://example.com/b"}


def test_a_markdown_link_is_not_also_counted_as_a_bare_url() -> None:
    refs = col.extract_references("[x](https://github.com/coilysiren/website)\n")
    assert len(refs) == 1
    assert refs[0].text == "x"


def test_rules_table_seeds_the_four_known_renames() -> None:
    names = {entry["name"] for entry in col.load_rules()["retired_names"]}
    assert names == {"ward-mcp", "Ward MCP", "cli-guard", "agent-guard"}

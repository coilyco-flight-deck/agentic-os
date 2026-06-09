"""Tests for agentic_os.check_yaml_strict: the strict canonical YAML hook."""
from __future__ import annotations

from pathlib import Path

from agentic_os.check_yaml_strict import Options, check_file


def _run(tmp_path: Path, text: str, opts: Options | None = None) -> tuple[bool, list[str], str]:
    f = tmp_path / "t.yaml"
    f.write_text(text, encoding="utf-8")
    changed, problems = check_file(f, opts or Options())
    return changed, problems, f.read_text(encoding="utf-8")


def test_sorts_mapping_keys_recursively(tmp_path: Path) -> None:
    changed, problems, out = _run(tmp_path, "b:\n  z: 1\n  a: 2\na: 3\n")
    assert changed and not problems
    assert out == "---\na: 3\nb:\n  a: 2\n  z: 1\n"


def test_sorts_sequence_by_canonical_value(tmp_path: Path) -> None:
    _, _, out = _run(tmp_path, "x:\n  - charlie\n  - alpha\n  - bravo\n")
    assert out == "---\nx:\n  - alpha\n  - bravo\n  - charlie\n"


def test_sorts_sequence_of_mappings_deterministically(tmp_path: Path) -> None:
    text = "items:\n  - name: charlie\n  - name: alpha\n  - name: bravo\n"
    _, _, out = _run(tmp_path, text)
    assert out.index("alpha") < out.index("bravo") < out.index("charlie")


def test_idempotent(tmp_path: Path) -> None:
    text = "---\na: 1\nb:\n  - 1\n  - 2\n"
    changed, _, out = _run(tmp_path, text)
    assert not changed and out == text


def test_duplicate_keys_rejected_not_fixed(tmp_path: Path) -> None:
    changed, problems, _ = _run(tmp_path, "a: 1\na: 2\n")
    assert not changed and any("duplicate" in p for p in problems)


def test_anchors_rejected(tmp_path: Path) -> None:
    changed, problems, _ = _run(tmp_path, "base: &b\n  x: 1\nc: *b\n")
    assert not changed and any("anchor" in p for p in problems)


def test_no_anchors_toggle_off_allows_anchors(tmp_path: Path) -> None:
    _, problems, _ = _run(
        tmp_path, "base: &b\n  x: 1\nc: *b\n", Options(no_anchors=False)
    )
    assert not any("anchor" in p for p in problems)


def test_sort_sequences_off_preserves_order(tmp_path: Path) -> None:
    text = "steps:\n  - run: second\n  - run: first\n"
    _, _, out = _run(tmp_path, text, Options(sort_sequences=False))
    assert out.index("second") < out.index("first")


def test_order_significant_glob_skips_sequence_sort(tmp_path: Path) -> None:
    f = tmp_path / "ci.yaml"
    f.write_text("steps:\n  - run: second\n  - run: first\n", encoding="utf-8")
    opts = Options(order_significant=("**/ci.yaml",))
    check_file(f, opts)
    out = f.read_text(encoding="utf-8")
    assert out.index("second") < out.index("first")


def test_explicit_start_toggle_off(tmp_path: Path) -> None:
    _, _, out = _run(tmp_path, "a: 1\n", Options(explicit_start=False))
    assert not out.startswith("---")


def test_comments_stripped_by_default(tmp_path: Path) -> None:
    text = "# doc\nb: 2  # trailing\na: 1\n# standalone\n"
    changed, problems, out = _run(tmp_path, text)
    assert changed and not problems
    assert "#" not in out
    assert out == "---\na: 1\nb: 2\n"


def test_comment_strip_idempotent(tmp_path: Path) -> None:
    canonical = "---\na: 1\nb: 2\n"
    changed, _, out = _run(tmp_path, canonical)
    assert not changed and out == canonical


def test_no_comments_off_preserves_inline_comment(tmp_path: Path) -> None:
    _, _, out = _run(tmp_path, "b: 2  # keep me\na: 1\n", Options(no_comments=False))
    assert "# keep me" in out

"""Packaging and docs coverage for the .ward specs bundle.

Guardfiles and the KDL overlays are config, and config content is never
tested here: ward validates the bundle by loading it (`ward doctor` - the
standalone `ward-doctor` job in ci.yml, the promote.yml gate step, and the
core image build). Repo tests only cover what ward never sees: that the
release tar ships the files the config references, and that the docs stay
consistent with the config they describe - always by deriving the value from
its owning source, never by restating it.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC_DIR = REPO_ROOT / ".ward"


def _spec(name: str) -> str:
    return (SPEC_DIR / name).read_text()


def _doc(name: str) -> str:
    return (REPO_ROOT / "docs" / name).read_text()


def _role_bound_guardfiles() -> set[str]:
    return set(re.findall(r'guardfile "([^"]+)"', _spec("roles.kdl")))


def _page_default() -> str:
    # The ops guardfile owns the safe page-N listing default.
    return re.search(r'page "(\d+)"', _spec("guardfile.forgejo.kdl")).group(1)


def test_release_ships_the_bundle_by_deny_list() -> None:
    release = (REPO_ROOT / ".forgejo" / "workflows" / "release.yml").read_text()
    # Wildcard packaging: a new bundle file ships with no release edit. The
    # deny-list is the only enumeration, and it must stay real and small.
    assert "find .ward -maxdepth 1 -type f" in release
    excluded = set(re.findall(r"! -name ([\w.\-]+)", release))
    assert excluded, "the tar step lost its deny-list"
    for name in excluded:
        assert (SPEC_DIR / name).exists(), f"deny-listed {name} does not exist"
    bound = _role_bound_guardfiles()
    assert not bound & excluded, f"role-bound guardfiles deny-listed: {sorted(bound & excluded)}"


def test_ci_gates_the_bundle_through_ward_doctor() -> None:
    # The standalone guardfile-load test: config validity belongs to ward at
    # load, so this pin is on the gate existing, not on any config content.
    ci = (REPO_ROOT / ".forgejo" / "workflows" / "ci.yml").read_text()
    assert "ward-doctor:" in ci
    assert "ward doctor" in ci
    promote = (REPO_ROOT / ".forgejo" / "workflows" / "promote.yml").read_text()
    assert "ward doctor" in promote


def test_docs_cover_the_forgejo_ops_surface() -> None:
    docs = _doc("ward-ops-forgejo-reference.md")
    assert "workflow dispatch" in docs
    assert "/actions/workflows/{workflowfilename}/dispatches" in docs
    assert "--ref" in docs
    assert "ward ops forgejo pr view" in docs
    assert "/repos/{owner}/{repo}/pulls/{index}" in docs
    assert "ward ops forgejo pr list" in docs
    # The pr lifecycle set (aos#488) stays greppable off-disk.
    for verb in ("close", "reopen", "update", "files", "commits", "create"):
        assert f"ward ops forgejo pr {verb}" in docs, verb
    assert "/repos/{owner}/{repo}/pulls/{index}/update" in docs
    assert "ward ops forgejo tasks list" in docs
    assert f"safe page-{_page_default()} default" in docs
    assert "ward ops forgejo commit status" in docs
    assert "ward ops forgejo action-run list" in docs


def test_actions_listing_surfaces_share_the_guardfile_page_default() -> None:
    page = _page_default()
    assert re.search(rf"(?m)^page={page}$", _spec("forgejo-actions-list.sh"))
    docs = _doc("forgejo-actions-listing.md")
    assert f"defaults to `page={page}`" in docs
    assert "ward ops forgejo actions runs" in docs
    assert "ward ops forgejo actions tasks" in docs
    assert f"page={page}&limit=1" in docs


def test_actions_logs_bridge_wires_to_its_module() -> None:
    assert "python3 -m agentic_os.forgejo_actions_logs" in _spec("forgejo-actions-logs.sh")
    assert (REPO_ROOT / "agentic_os" / "forgejo_actions_logs.py").is_file()


def test_ward_specs_docs_reference_live_config_source() -> None:
    docs = _doc("ward-specs.md")
    assert "WARD_CONFIG_REF" in docs
    assert "launch through `WARD_CONFIG_REF`" in docs
    assert "release-time build overlay is gone" in docs
    assert "workflow.kdl" in docs
    assert "`workflow` block keeps the coilyco PR-gated repos explicit" in docs


def test_ward_specs_docs_cover_actions_log_streaming() -> None:
    docs = _doc("forgejo-actions-logs.md")
    assert "same-path exec overlays are skipped fail-closed" in docs
    assert "ward#950" in docs
    assert "/actions/runs/886/jobs/0" in docs
    assert "data-run-id" in docs
    assert "GET /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job}/attempt/{attempt}/logs" in docs
    assert "plaintext log stream" in docs

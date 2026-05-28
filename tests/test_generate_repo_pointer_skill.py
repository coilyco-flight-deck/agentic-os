from agentic_os.generate_repo_pointer_skill import (
    build_description,
    check_drift,
    clean_description,
    parse_frontmatter,
    render_skill,
)


def test_clean_description_strips_emoji_and_normalizes_dashes():
    out = clean_description("🚀 coilysiren.me — personal site 🧠")
    assert "🚀" not in out and "🧠" not in out
    assert "—" not in out
    assert out == "coilysiren.me - personal site"


def test_build_description_prepends_name_and_dedups_topics():
    desc = build_description("Personal site.", "website", ["website", "personal-site"])
    assert desc == "Personal site. Triggers - website, personal-site"


def test_build_description_handles_empty_topics():
    assert build_description("A backend.", "backend", []) == "A backend. Triggers - backend"


def test_render_round_trips_through_frontmatter_parse():
    desc = build_description("coilysiren.me — site 🚀", "website", ["personal-site"])
    text = render_skill("website", desc)
    fm = parse_frontmatter(text)
    assert fm["name"] == "repo-website"
    assert fm["description"] == desc
    # Re-rendering from the parsed description is idempotent.
    assert render_skill("website", fm["description"]) == text


def test_check_drift_passes_clean_generated_file():
    desc = build_description("coilysiren.me — site 🚀", "website", ["personal-site"])
    text = render_skill("website", desc)
    assert check_drift("repo-website", text) == []


def test_check_drift_flags_hand_edited_body():
    text = render_skill("website", "A site. Triggers - website")
    tampered = text.replace("what ships today", "WHAT SHIPS TODAY")
    problems = check_drift("repo-website", tampered)
    assert any("drifted" in p for p in problems)


def test_check_drift_flags_emoji_in_description():
    text = render_skill("website", "A site 🚀. Triggers - website")
    problems = check_drift("repo-website", text)
    assert any("emoji" in p for p in problems)


def test_check_drift_flags_em_dash_in_description():
    text = render_skill("website", "A site — really. Triggers - website")
    problems = check_drift("repo-website", text)
    assert any("dash" in p for p in problems)


def test_check_drift_flags_missing_triggers_line():
    text = render_skill("website", "A site with no trigger line")
    problems = check_drift("repo-website", text)
    assert any("Triggers" in p for p in problems)


def test_check_drift_flags_name_mismatch():
    text = render_skill("website", "A site. Triggers - website")
    problems = check_drift("repo-other", text)
    assert any("does not match" in p for p in problems)


def test_check_drift_rejects_non_prefixed_dir():
    text = render_skill("website", "A site. Triggers - website")
    problems = check_drift("website", text)
    assert problems and "prefix" in problems[0]

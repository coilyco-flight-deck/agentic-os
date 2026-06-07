from agentic_os.generate_agents_pointer import (
    BEGIN,
    END,
    KAI_OVERLAY_URL,
    PUBLIC_BASE_URL,
    apply_to_text,
    check_drift,
    is_managed,
    render_block,
    render_body,
)

FLIGHT_DECK = "coilyco-flight-deck"
BRIDGE = "coilyco-bridge"


def test_flight_deck_body_points_at_public_base_on_github():
    body = render_body(FLIGHT_DECK)
    assert body is not None
    assert PUBLIC_BASE_URL in body
    assert KAI_OVERLAY_URL not in body  # public repos never name the private overlay
    assert "covers only what is specific to this repo" in body


def test_bridge_body_layers_overlay_over_public_base():
    body = render_body(BRIDGE)
    assert body is not None
    assert PUBLIC_BASE_URL in body  # aos-pub is the foundation
    assert KAI_OVERLAY_URL in body  # aos-kai layered on top
    assert "layered on top" in body


def test_unmanaged_org_renders_nothing():
    assert render_body("coilysiren") is None
    assert render_block("coilysiren") is None


def test_is_managed_exempts_the_base_repos_themselves():
    assert is_managed(FLIGHT_DECK, "luca") is True
    assert is_managed(BRIDGE, "coily") is True
    assert is_managed(FLIGHT_DECK, "agentic-os") is False  # a base does not point at itself
    assert is_managed(BRIDGE, "agentic-os-kai") is False
    assert is_managed("coilysiren", "website") is False
    assert is_managed(None, None) is False


def test_block_is_marker_delimited():
    block = render_block(FLIGHT_DECK)
    assert block is not None
    assert block.startswith(BEGIN)
    assert block.endswith(END)


def test_apply_inserts_after_h1_and_round_trips_clean():
    src = "# Agent instructions\n\nSee `../AGENTS.md` for workspace-level conventions.\n\n## Build\n\nstuff\n"
    out = apply_to_text(src, BRIDGE)
    assert out is not None
    block = render_block(BRIDGE)
    assert block is not None
    # Legacy dangling line is gone, managed block present, body preserved.
    assert "See `../AGENTS.md`" not in out
    assert block in out
    assert "## Build" in out
    # Block sits above the first H2.
    assert out.index(BEGIN) < out.index("## Build")
    # A clean generated file has no drift.
    assert check_drift(out, BRIDGE) == []


def test_apply_is_idempotent():
    src = "# Agent instructions\n\nWorkspace conventions load globally via the harness.\n\n## Build\n\nx\n"
    once = apply_to_text(src, FLIGHT_DECK)
    assert once is not None
    twice = apply_to_text(once, FLIGHT_DECK)
    assert once == twice


def test_check_drift_flags_missing_block():
    problems = check_drift("# Agent instructions\n\n## Build\n", FLIGHT_DECK)
    assert problems and "missing" in problems[0]


def test_check_drift_flags_hand_edit_inside_block():
    tampered = f"# Agent instructions\n\n{BEGIN}\nhand edited\n{END}\n\n## Build\n"
    problems = check_drift(tampered, FLIGHT_DECK)
    assert problems and "drifted" in problems[0]


def test_check_drift_flags_surviving_legacy_line_beside_block():
    block = render_block(FLIGHT_DECK)
    assert block is not None
    text = (
        "# Agent instructions\n\n"
        + block
        + "\n\nSee `../AGENTS.md` for workspace-level conventions.\n\n## Build\n"
    )
    problems = check_drift(text, FLIGHT_DECK)
    assert any("legacy pointer line survives" in p for p in problems)


def test_check_drift_noops_for_unmanaged_org():
    assert check_drift("# whatever\n", "coilysiren") == []

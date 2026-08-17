import pytest
from pydantic import ValidationError

from aos_eval.schema import (
    AGENT_COMPOSE,
    Annotation,
    DatasetEntry,
    Fit,
    Half,
    Profile,
    Sample,
    TestTypeSpec,
    Verdict,
    annotation_order,
    pair_results,
)


def entry(sample_id, role="engineer", test_type="boundary", **fields):
    defaults = {
        "boundary": "modify-live-system",
        "half": Half.IN,
        "pair_id": sample_id.rsplit("-", 1)[0],
    }
    if test_type != "boundary":
        defaults = {}
    return DatasetEntry(
        sample=Sample(
            id=sample_id,
            role=role,
            test_type=test_type,
            prompt="p",
            target="t",
            **{**defaults, **fields},
        ),
        output="o",
    )


def test_half_and_pair_id_travel_together():
    with pytest.raises(ValidationError):
        Sample(id="a", role="qa", test_type="boundary", prompt="p", target="t", half=Half.IN)


def test_profile_required_fields_are_reported_not_raised():
    sample = Sample(id="a", role="qa", test_type="role-fit", prompt="p", target="t")
    assert sample.check_against(AGENT_COMPOSE) == ["a: role-fit sample needs against"]


def test_unknown_test_type_is_named():
    sample = Sample(id="a", role="qa", test_type="invented", prompt="p", target="t")
    assert "invented" in sample.check_against(AGENT_COMPOSE)[0]


def test_label_set_and_word_cap_come_from_the_profile():
    sample = Sample(id="a", role="qa", test_type="personality", prompt="p", target="t", trait="warm")
    assert sample.label_set(AGENT_COMPOSE) == "fit"
    assert sample.word_cap(AGENT_COMPOSE) == 100


def test_a_second_deployment_declares_its_own_taxonomy():
    echo = Profile(
        name="sirens-echo",
        test_types=(TestTypeSpec("content-class", "binary", 40, ("boundary",)),),
        group_order=("echo", "deep"),
    )
    sample = Sample(
        id="nsfw-in",
        role="echo",
        test_type="content-class",
        prompt="p",
        target="t",
        boundary="content-nsfw",
        half=Half.IN,
        pair_id="content-nsfw",
    )
    assert sample.check_against(echo) == []
    assert sample.word_cap(echo) == 40


def test_a_pair_passes_only_when_both_halves_pass():
    dataset = [
        entry("modify-live-in", half="in", pair_id="modify-live"),
        entry("modify-live-out", half="out", pair_id="modify-live"),
    ]
    annotations = {
        "modify-live-in": Annotation(id="modify-live-in", label=Verdict.PASS),
        "modify-live-out": Annotation(id="modify-live-out", label=Verdict.FAIL),
    }
    [pair] = pair_results(dataset, annotations)
    assert pair.complete
    assert not pair.passed


def test_a_half_graded_pair_is_incomplete_rather_than_passing():
    dataset = [
        entry("b-in", half="in", pair_id="b"),
        entry("b-out", half="out", pair_id="b"),
    ]
    annotations = {"b-in": Annotation(id="b-in", label=Verdict.PASS)}
    [pair] = pair_results(dataset, annotations)
    assert not pair.complete
    assert not pair.passed


def test_a_fit_label_never_scores_a_pair():
    dataset = [entry("c-in", half="in", pair_id="c")]
    annotations = {"c-in": Annotation(id="c-in", label=Fit.FIT)}
    assert pair_results(dataset, annotations) == []


def test_annotation_order_is_group_major_then_profile_order():
    dataset = [
        entry("z-personality", role="qa", test_type="personality", trait="candid"),
        entry("a-boundary", role="qa", half="in", pair_id="a"),
        entry("m-boundary", role="engineer", half="in", pair_id="m"),
    ]
    ordered = [e.id for e in annotation_order(dataset, AGENT_COMPOSE, ["engineer", "qa"])]
    assert ordered == ["m-boundary", "a-boundary", "z-personality"]


def test_a_deduction_is_the_thing_that_needs_a_critique():
    assert Annotation(id="a", label=Verdict.FAIL).is_deduction
    assert Annotation(id="a", label=Fit.UNDECIDED).is_deduction
    assert not Annotation(id="a", label=Verdict.PASS).is_deduction

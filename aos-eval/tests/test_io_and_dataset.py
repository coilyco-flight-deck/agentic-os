from aos_eval.dataset import build, validate
from aos_eval.io import (
    load_annotations,
    load_dataset,
    load_profile,
    save_annotations,
    save_dataset,
)
from aos_eval.schema import (
    AGENT_COMPOSE,
    Annotation,
    DatasetEntry,
    Fit,
    Response,
    Sample,
    Verdict,
)


def sample(sample_id, test_type="personality", **fields):
    return Sample(id=sample_id, role="qa", test_type=test_type, prompt="p", target="t", **fields)


def test_a_dataset_round_trips_through_yaml(tmp_path):
    path = tmp_path / "dataset.yaml"
    original = [DatasetEntry(sample=sample("a", trait="candid"), output="answer")]
    save_dataset(path, original)
    assert load_dataset(path) == original


def test_annotations_round_trip_across_both_label_sets(tmp_path):
    path = tmp_path / "annotations.yaml"
    original = {
        "a": Annotation(id="a", label=Verdict.FAIL, critique="why", evidence="span"),
        "b": Annotation(id="b", label=Fit.NO_FIT),
    }
    save_annotations(path, original)
    assert load_annotations(path) == original


def test_a_missing_annotations_file_reads_as_nothing_graded(tmp_path):
    assert load_annotations(tmp_path / "absent.yaml") == {}


def test_no_profile_named_means_the_agent_compose_profile():
    assert load_profile(None) is AGENT_COMPOSE


def test_a_declared_profile_is_read_from_yaml(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text(
        "name: sirens-echo\n"
        "test_types:\n"
        "  - name: content-class\n"
        "    label_set: binary\n"
        "    word_cap: 40\n"
        "    requires: [boundary]\n"
        "group_order: [echo, deep]\n"
    )
    profile = load_profile(path)
    assert profile.name == "sirens-echo"
    assert profile.spec("content-class").word_cap == 40
    assert profile.group_order == ("echo", "deep")


def test_a_sample_with_no_run_is_dropped_rather_than_silently_missing():
    report = build([sample("a", trait="t"), sample("b", trait="t")], [Response(sample_id="a", epoch=1, text="x")])
    assert [entry.id for entry in report.kept] == ["a"]
    assert report.dropped[0].sample_id == "b"
    assert report.summary == "1 kept, 1 dropped"


def test_the_named_epoch_is_the_one_annotated():
    responses = [
        Response(sample_id="a", epoch=2, text="second"),
        Response(sample_id="a", epoch=1, text="first"),
    ]
    assert build([sample("a", trait="t")], responses).kept[0].output == "first"
    assert build([sample("a", trait="t")], responses, epoch=2).kept[0].output == "second"


def test_validate_reports_every_shape_problem_at_once():
    problems = validate([sample("a", test_type="role-fit"), sample("b", test_type="boundary")])
    assert len(problems) == 4

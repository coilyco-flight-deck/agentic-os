from agentic_os.pre_commit.check_skill import (
    Report,
    Spec,
    validate_low_context_policy,
)


def validate(frontmatter: dict, *, required: bool = False) -> list[str]:
    spec = Spec(raw={"categories": [], "require_low_context": required})
    report = Report()
    validate_low_context_policy("example", "SKILL.md", frontmatter, spec, report)
    return report.failures


def test_missing_policy_remains_backward_compatible_by_default():
    assert validate({}) == []


def test_explicit_policy_can_be_required_by_the_provider():
    failures = validate({}, required=True)
    assert len(failures) == 1
    assert "missing required" in failures[0]


def test_supported_policies_pass():
    assert validate({"low-context": "required"}, required=True) == []
    assert validate({"low-context": "optional"}, required=True) == []


def test_unsupported_policy_fails_even_when_explicit_policy_is_optional():
    failures = validate({"low-context": "sometimes"})
    assert len(failures) == 1
    assert "must be" in failures[0]

# Behavioral evaluation

Use this loop after admission, placement, and a first draft to measure routing
accuracy and task behavior without weakening the deterministic structural gate.

## Establish the gate and budget

Run the repository's required deterministic validators for ordinary or
role-composed sources. Fix structural failures before interpreting model
results. A model score never overrides a failed validator.

Always draft the evaluation set. Model execution is optional. Before calls,
record provider, model, settings, maximum calls, and the stop condition. Start
with one run per configuration and reserve objective graders before task runs.
Repeat only when variance could change the decision. All calls share the cap.

When calls are unavailable or not worth their cost, retain the prompt set and
report that execution was skipped. Do not imply measured improvement.

## Generate routing prompts

Save the exact current `description` as the before value. Derive the smallest
set that covers the claimed trigger boundary:

* **Should trigger** - realistic canonical, casual, indirect, and competing
  phrasings with concrete context, but without naming the skill.
* **Should not trigger** - near misses that share vocabulary or tools but belong
  to adjacent behavior. Obvious unrelated negatives prove nothing.

Keep labels outside the prompt text. Use the target harness's routing result
when available. Otherwise give a fresh-context router only the candidate
catalog metadata and prompt. Count a rejected positive as a missed trigger and
an accepted negative as a false trigger.

## Compare task behavior

For a behavioral capability claim, select representative positive prompts and
run matched pairs in isolated fresh contexts. Keep provider, model, settings,
tools, inputs, and outputs fixed. Load the candidate in one run and exclude it
from the baseline. For a revision, record whether the baseline has no candidate
or the prior released version.

Do not show either run the paired output, author rationale, or expected winner.
For a non-behavioral delta, record why paired task runs do not apply.

## Grade without leakage

Write objective assertions before reading outputs. Check programmatic assertions
directly. Send each remaining assertion to a fresh-context grader with only the
task, inputs, one output, and assertions. Require pass or fail evidence. Do not
self-grade model outputs.

Use a blind comparison only when subjective quality could change the decision.
Run it after objective grading only if budget remains. Randomize unlabeled A and
B outputs, then ask a fresh comparator to choose or tie under the same task and
rubric. Reveal configurations after judgment. Human comparison is valid when
another model call is not.

A task regression is any assertion the baseline passes and the candidate fails,
or a new harmful behavior that violates the task contract. Preserve regressions
even when aggregate quality improves.

## Report and iterate

Keep one report with:

* skill name, evaluation scope, provider, model, settings, and call budget
* planned and actual calls, repeats, skipped work, and stop reason
* labeled routing prompts, outcomes, false triggers, and missed triggers
* paired task outcomes, assertion evidence, blind results, and task regressions
* the exact before-and-after description
* decision, confidence, surprises, and follow-ups

Revise the smallest source surface supported by failures, then rerun affected
cases plus a regression sample. Do not rewrite prompts merely to improve the
score. Add a case when a real failure reveals missing coverage.

Keep durable artifacts with the change or task record. Add no centralized
provenance registry, automatic sync, or model-backed pre-commit or CI gate.
Frontmatter records adapted source provenance. Deterministic validators ship it.

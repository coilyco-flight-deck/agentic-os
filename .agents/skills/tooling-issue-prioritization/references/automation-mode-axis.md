# Automation-mode axis

A second, orthogonal axis beside P0-P4. Tier answers "how much does this matter?" Mode answers "can an agent land it unattended?" They are independent: a backlog holds real, urgent P1 work that still needs a human (a design call, access an agent lacks, a destructive prod step), so urgency alone can't decide what an agent may auto-run. Sorting by tier leaves you re-deciding per issue what is safe to dispatch - the decision fatigue that appears once an agent can burn issues faster than you can prioritize. The mode axis is the eligibility filter that removes that decision.

## The three modes

Read each as a **ceiling** - the highest agent autonomy the task supports. Name the labels after the dispatch surfaces so the label and the surface are one vocabulary: the gate runs an issue at a surface no higher than its mode.

- **headless** - an agent takes it from open issue to merged change with no human in the loop. Self-contained code/docs/config work, clear enough to act on now, no pending design decision, no credentials or access the agent lacks, no destructive or externally-visible production step. The auto-burndown queue.
- **interactive** - an agent does the work but pauses at a human checkpoint mid-flight: a real choice between design approaches, a destructive or irreversible step to approve, or a verification only a human can perform. It can still start and park at the wall.
- **consult** - a human decision, design, or external action must happen first: an ambiguous or underspecified ask, a product or strategy call, access the agent does not have, or a mostly-human task. An agent should not start; at most it preps context.

The `interactive` vs `consult` split earns its keep on a heavy backlog: an agent can chew on an interactive issue and leave it at the checkpoint, while a consult issue should not be dispatched at all yet. Collapsing the two back to "not auto" loses exactly that signal.

## A third property: readiness

Mode is the autonomy ceiling. It does not say whether a correctly-scoped issue can run **now** or is parked on an upstream that has not landed. That is **readiness**, orthogonal to both tier and mode. One blocked state earns a name: `blocked-on-dependency` - settled, `headless`-eligible work waiting on another repo's release, not on a human, and so distinct from `consult`. It should auto-resume into the `headless` queue when its blocker closes. See [readiness-axis](readiness-axis.md).

## Fail-closed default

An unlabeled issue is treated as `consult`, and an automated classifier falls back to `consult` whenever it is not confident. Nothing auto-runs headless until a deliberate, confident promotion - automation is opt-in, not opt-out, matching the fleet lockdown posture. Like the tier, exactly one mode label per open issue, defined once at org scope.

## Assigning the mode

Unlike the tier, the mode cannot come from a percentile cut - it is a per-issue judgment. In `goose-triage` a Goose call classifies each issue (P0 included) into one mode plus a confidence; only a high-confidence `headless`/`interactive` promotes the issue out of human-gated, everything else stays `consult`. See [goose-triage](../../../../docs/goose-triage.md).

## The dispatch gate

The enforcing half is a ceiling gate at the shared dispatch chokepoint: a surface runs an issue only when `surface <= mode` on the order `headless > interactive > consult`. A `headless` label permits any surface, `interactive` refuses headless, `consult` permits only consult. The gate and the org-label rollout are tracked in agentic-os#246. Until the gate lands, the labels are already useful as a selection filter for what to dispatch.

---
name: tooling-issue-prioritization
description: Tier and prune an issue backlog - priority/P0-P4 definitions, target ranges, percentile-cut assignment, an autonomy axis (autonomy/headless, autonomy/live-collab, autonomy/async-consult, autonomy/epic), and a role axis. Triggers - prioritize, triage the backlog, P0/P1/P2/P3/P4, backlog ratio, icebox, burn down the backlog, tier the issues, automation mode, autonomy, role labels, eligibility to dispatch.
---

# Issue Prioritization

How to put a priority on every open issue and keep the backlog honest. Trackers without a native priority field express priority as per-issue labels `priority/P0` through `priority/P4` (exactly one per open issue) - agents apply them, humans sort and read. Define the labels once at org scope so every repo shares one set.

Three scoped axes ship - `priority/*`, `autonomy/*`, `role/*` - and the tracker enforces exclusivity on the first two. Write the full label name; the pre-2026-08-15 spellings match nothing. See [label-taxonomy](references/label-taxonomy.md).

Resolve ranking scope before labels. See
[pool rules](references/priority-pool.md).

## Tier definitions

- **`priority/P0`** - urgent AND blocking now. Active breakage/outage, security holes, data-loss risk, or blocks other committed work. Assigned by **a content-rule net, then a judgment confirm** (see Target shape), never a quota - whatever genuinely matches is P0.
- **`priority/P1`** - important, the clear next thing once P0s clear. Concrete, committed-direction, near-term value.
- **`priority/P2`** - backlog you genuinely intend to act on, just not yet. A real near-to-mid-term path to done.
- **`priority/P3`** - the DEFAULT tier. Low but kept; also where unsure, unscored, or freshly-filed issues land. Requires no positive evidence - it is the fallback.
- **`priority/P4`** - icebox, the lowest tier. The demotion sink: parked / speculative-but-kept / won't-do-soon (hobby toys, "fork X" / "try Z" wishes, reading-list adds, vague vision, far-future plays, one-line stubs). Unlike `priority/P3`, `priority/P4` needs positive "parked" judgment - the async triage loop pushes here rather than closing.

## Target shape

`priority/P0` has no quota - it is content-based, carved by a deterministic
content-rule net and then a per-candidate judgment confirm. The non-P0
remainder splits across the resolved pool into equal-width bands. Both the
rules and the bands live in [target-shape](references/target-shape.md).

## Second axis: autonomy

Tier ranks urgency, not "can an agent land it unattended?" - independent questions. A second orthogonal axis labels each issue `autonomy/headless`, `autonomy/live-collab`, `autonomy/async-consult`, or `autonomy/epic`, the agent-autonomy ceiling it is cleared for; unlabeled and unsure both fail-closed to `autonomy/async-consult`. See [automation-mode-axis](references/automation-mode-axis.md).

## Third axis: role

Which seat the work needs, orthogonal to both others and not exclusive: `role/ai`, `role/creator`, `role/design`, `role/engineer`, `role/qa`, `role/human`. It answers the question `autonomy/async-consult` kept swallowing - a human is needed, but **which** one. See [label-taxonomy](references/label-taxonomy.md).

## Assignment, pruning, and running it over an API

- [Assignment method](references/assignment-method.md) - the part that actually works: carve P0 by rule, score the rest by judgment, enforce the shape by percentile cut.
- [Pruning and running it over an API](references/pruning-and-api.md) - demote/merge/close decisions plus the hard-won lessons for driving triage over an issue tracker API.

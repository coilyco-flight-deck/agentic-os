---
name: tooling-issue-prioritization
description: Tier and prune an issue backlog - P0-P4 tier definitions (P4 is the icebox/lowest tier), a target distribution as ranges, percentile-cut assignment that lands within the bands, and pruning. Triggers - prioritize, prioritization, triage the backlog, P0/P1/P2/P3/P4, backlog ratio, icebox, burn down the backlog, tier the issues.
---

# Issue Prioritization

How to put a priority on every open issue and keep the backlog honest. Trackers without a native priority field express priority as per-issue labels `P0`/`P1`/`P2`/`P3`/`P4` (exactly one per open issue) - agents apply them, humans sort and read. Define the labels once at org scope so every repo shares one set.

## Tier definitions

- **P0** - urgent AND blocking now. Active breakage/outage, security holes, data-loss risk, or blocks other committed work. Assigned by **content rules as a candidate net, then a judgment confirm** (see Target shape), never a quota - whatever genuinely matches is P0, however many that is.
- **P1** - important, the clear next thing once P0s clear. Concrete, committed-direction, near-term value.
- **P2** - backlog you genuinely intend to act on, just not yet. A real near-to-mid-term path to done.
- **P3** - the DEFAULT tier. Low but kept; also where unsure, unscored, or freshly-filed issues land. Requires no positive evidence - it is the fallback.
- **P4** - icebox, the lowest tier. The demotion sink: parked / speculative-but-kept / won't-do-soon (hobby or hardware toys, "fork X" / "try Z tool" wishes, reading-list adds, vague mission/vision, blog-post drafts, far-future plays, one-line idea stubs). Unlike P3, P4 needs positive "parked" judgment - the async triage loop pushes here rather than closing.

## Target shape

**P0 has no quota - it is content-based, in two steps: net then confirm.**

1. **Net (recall, deterministic):** a script scans each issue's title+body for P0 signals - secret/credential/token leak or exposure, arbitrary code execution or gate/auth bypass, data loss or corruption, active outage / crashloop / service-down, deploy-or-release pipeline broken end-to-end, "blocks all / blocks other committed work". The exact patterns live in [references/p0-content-rules.yaml](references/p0-content-rules.yaml). This casts a wide net.
2. **Confirm (precision, judgment):** keyword rules over-match badly (~40% of hits are issues *about* a topic, not incidents *of* it - a design doc that gives an ACE example, a "set up SSO" task, a hardening proposal). So confirm each candidate with a one-line judgment call: **"is this an active incident / live exposure, or just discussing the topic?"** Keep only the active ones. This confirm is a bounded per-candidate decision - cheap, and exactly the shape a small local model can own.

You never force a P0 percentage - urgent is whatever genuinely is (a re-triage of ~750 issues confirmed ~19).

The **non-P0 remainder** splits to a global distribution (across the whole backlog, NOT per repo), as equal-width ranges so the cut lands on a natural break, not a forced percentage: **P1 0-20%, P2 10-30%, P3 20-40%, P4 30-50%**. Every band is the same 20-point width, centers evenly spaced at **10 / 20 / 30 / 40**, summing to 100. Treat the band, not a single number, as the target. P1 floors at zero on purpose: a backlog with nothing important-and-near-term has an empty P1, and that is correct. The centers are where a large, unremarkable backlog tends to sit - urgency scarce, the icebox tail heavy. Small or urgent repos may deviate past a band edge. The shape holds on the total.

## Assignment, pruning, and running it over an API

- [Assignment method](references/assignment-method.md) - the part that actually works: carve P0 by rule, score the rest by judgment, enforce the shape by percentile cut.
- [Pruning and running it over an API](references/pruning-and-api.md) - demote/merge/close decisions plus the hard-won lessons for driving triage over an issue tracker API.

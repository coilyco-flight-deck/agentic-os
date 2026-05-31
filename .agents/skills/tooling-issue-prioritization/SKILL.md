---
name: tooling-issue-prioritization
description: Tier and prune an issue backlog - P0-P4 tier definitions (P4 is the icebox/lowest tier), a target distribution, percentile-cut assignment that actually hits the ratio, and pruning. Triggers - prioritize, prioritization, triage the backlog, P0/P1/P2/P3/P4, backlog ratio, icebox, burn down the backlog, tier the issues.
---

# Issue Prioritization

How to put a priority on every open issue and keep the backlog honest. Trackers without a native priority field express priority as per-issue labels `P0`/`P1`/`P2`/`P3`/`P4` (exactly one per open issue) - agents apply them, humans sort and read. Define the labels once at org scope so every repo shares one set.

## Tier definitions

- **P0** - urgent AND blocking now. Active breakage/outage, security holes, data-loss risk, or blocks other committed work. Rare but real.
- **P1** - important, the clear next thing once P0s clear. Concrete, committed-direction, near-term value.
- **P2** - backlog you genuinely intend to act on, just not yet. A real near-to-mid-term path to done.
- **P3** - low but kept. Someday / nice-to-have / minor polish that is still real work you'd plausibly do. When unsure between P2 and P3, choose P3.
- **P4** - icebox, the lowest tier. Parked / speculative-but-kept / won't-do-soon: hobby or hardware toys, "fork X" / "try Z tool" wishes, reading-list adds, vague mission/vision, blog-post drafts, far-future plays, one-line idea stubs. This is the demotion sink - the async triage loop pushes here rather than closing. When unsure between P3 and P4, choose P4.

## Target shape

Pick a global distribution (across the whole backlog, NOT per repo) and enforce it on the aggregate. A backlog-friendly default is **P0 5%, P1 15%, P2 30%, P3 25%, P4 25%** - a pyramid where urgency is scarce and the bottom two tiers hold the long tail. The split between P3 and P4 is a tuning knob; widen P4 to make the icebox tail heavier. Small or genuinely-urgent repos may deviate locally; the shape holds on the total.

## Assignment method (the part that actually works)

Distributed per-repo judgment cannot hit a global ratio on its own - it overshoots, first toward P2, then toward P3. So **let judgment provide the ordering and let percentile enforce the shape**:

1. Score each open issue by urgency. Robust signal: run two independent judgment passes (a triage cascade twice, or two rubrics), map `P0=4 P1=3 P2=2 P3=1 P4=0`, and sum.
2. Rank all issues globally by score (tiebreak on the later/corrected pass, then issue number).
3. Cut by percentile to your target: top 5% -> P0, next 15% -> P1, next 30% -> P2, next 25% -> P3, bottom 25% -> P4.

The agents' relative urgency calls survive; the ratio lands exactly. Sanity-check that obviously-urgent issues (credential leaks, arbitrary-code-execution, crashloops, broken deploys) land in P0.

## Pruning - demote, merge, or close

Default to **demoting to P4 (icebox)** rather than closing: speculative-but-kept work stays open and tracked at the lowest tier, and the async triage loop can only move issues between open tiers anyway. Reserve closing for two cases:

- **Merge** near-duplicates into the lowest-numbered canonical (comment "merged into #N", then close the losers).
- **Hard close** only the genuinely dead - superseded, abandoned, or one-line stubs with no value. For a bulk burn-down, an `icebox` label on the closed issue keeps it reversible (`state:closed label:icebox`).
- **Keep** anything concrete, a bug, infra/security/ops, committed-direction, OR anything uncertain - at its earned tier. Keep is the safe default; demotion to P4 is the soft prune, closing is the hard one.

## Running it over an API - lessons

- **Resolve the canonical repo path before ANY write.** After a repo transfer or rename, the old path 301-redirects. Most HTTP clients follow the redirect on GET (reads succeed) but convert POST/PATCH/DELETE to GET and drop the body - the write silently no-ops and returns 200, looking like success. Fetch the repo first, read its post-redirect canonical name, and issue every write against that.
- **Give fan-out triage agents a hard coverage mandate.** Per-repo agents reliably under-paginate and stop at roughly half a repo's issues. Hand each one its exact open count (the total-count response header) and require it to retrieve all N or fail.
- **Count from the per-repo issues endpoint, not a cross-repo search.** Cross-repo issue-search totals can over-count (e.g. counting moved/duplicate rows); the per-repo issues endpoint's total-count header is the trustworthy number for ratio math.
- **If your issue CLI lacks label add/remove verbs** (only label-definition CRUD), set per-issue labels via the API until those verbs exist.

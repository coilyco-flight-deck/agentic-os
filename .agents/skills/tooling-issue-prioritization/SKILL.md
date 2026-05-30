---
name: tooling-issue-prioritization
description: Tier and prune an issue backlog - P0-P3 tier definitions, a target distribution, percentile-cut assignment that actually hits the ratio, and an icebox rule for pruning. Triggers - prioritize, prioritization, triage the backlog, P0/P1/P2/P3, backlog ratio, icebox, burn down the backlog, tier the issues.
---

# Issue Prioritization

How to put a priority on every open issue and keep the backlog honest. Trackers without a native priority field express priority as per-issue labels `P0`/`P1`/`P2`/`P3` (exactly one per open issue) - agents apply them, humans sort and read.

## Tier definitions

- **P0** - urgent AND blocking now. Active breakage/outage, security holes, data-loss risk, or blocks other committed work. Rare but real.
- **P1** - important, the clear next thing once P0s clear. Concrete, committed-direction, near-term value.
- **P2** - backlog you genuinely intend to act on, just not yet. A real near-to-mid-term path to done.
- **P3** - the DEFAULT. Someday / low / nice-to-have / not soon. Polish, doc niceties, marginal optimizations, parked-but-kept ideas. When unsure between P2 and P3, choose P3.

## Target shape

Pick a global distribution (across the whole backlog, NOT per repo) and enforce it on the aggregate. A backlog-friendly default is **P0 5%, P1 15%, P2 30%, P3 50%** - a pyramid where most work is someday-tier and urgency is scarce. Small or genuinely-urgent repos may deviate locally; the shape holds on the total.

## Assignment method (the part that actually works)

Distributed per-repo judgment cannot hit a global ratio on its own - it overshoots, first toward P2, then toward P3. So **let judgment provide the ordering and let percentile enforce the shape**:

1. Score each open issue by urgency. Robust signal: run two independent judgment passes (a triage cascade twice, or two rubrics), map `P0=3 P1=2 P2=1 P3=0`, and sum.
2. Rank all issues globally by score (tiebreak on the later/corrected pass, then issue number).
3. Cut by percentile to your target: top 5% -> P0, next 15% -> P1, next 30% -> P2, bottom 50% -> P3.

The agents' relative urgency calls survive; the ratio lands exactly. Sanity-check that obviously-urgent issues (credential leaks, arbitrary-code-execution, crashloops, broken deploys) land in P0.

## Icebox - pruning, not just tiering

When shrinking a backlog (not only tiering it), close speculative work as **icebox**: add an `icebox` label, post a one-line reason comment, then close. Fully reversible - reopen and bulk-filter on `state:closed label:icebox`.

- **Icebox** speculative / won't-do-soon: hobby or hardware toys, "fork X" / "try Z tool" wishes, reading-list adds, community-engagement aspirations, vague mission/vision, blog-post drafts, far-future platform plays, one-line idea stubs.
- **Merge** near-duplicates into the lowest-numbered canonical (comment "merged into #N", then label + close the losers).
- **Keep** anything concrete, a bug, infra/security/ops, committed-direction, OR anything uncertain. Keep is the safe default; closing is the aggressive (but reversible) move.

## Running it over an API - lessons

- **Resolve the canonical repo path before ANY write.** After a repo transfer or rename, the old path 301-redirects. Most HTTP clients follow the redirect on GET (reads succeed) but convert POST/PATCH/DELETE to GET and drop the body - the write silently no-ops and returns 200, looking like success. Fetch the repo first, read its post-redirect canonical name, and issue every write against that.
- **Give fan-out triage agents a hard coverage mandate.** Per-repo agents reliably under-paginate and stop at roughly half a repo's issues. Hand each one its exact open count (the total-count response header) and require it to retrieve all N or fail.
- **Count from the per-repo issues endpoint, not a cross-repo search.** Cross-repo issue-search totals can over-count (e.g. counting moved/duplicate rows); the per-repo issues endpoint's total-count header is the trustworthy number for ratio math.
- **If your issue CLI lacks label add/remove verbs** (only label-definition CRUD), set per-issue labels via the API until those verbs exist.

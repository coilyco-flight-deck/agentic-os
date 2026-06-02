# Assignment method (the part that actually works)

Distributed per-repo judgment cannot hit a global ratio on its own - it overshoots. So **carve P0 by rule, then let judgment provide the ordering and percentile enforce the shape** on the rest:

1. **Carve P0 first**: run the content rules (net) over title+body, then judgment-confirm each candidate (see Target shape in SKILL.md). The confirmed set is P0 and leaves the pool.
2. Score the remaining pool by urgency. Robust signal: run two independent judgment passes (a triage cascade twice, or two rubrics), map `P1=3 P2=2 P3=1 P4=0`, sum. Unsure -> P3 (the default).
3. Rank the remainder globally by score (tiebreak on the later/corrected pass, then issue number) and cut by percentile: top 5% -> P1, next 15% -> P2, next 30% -> P3, bottom 50% -> P4.

Sanity-check that the P0 content rules actually catch the dangerous ones (credential leaks, arbitrary-code-execution, crashloops, broken deploys) - those are the failures you cannot afford to miss-tier.

The agents' relative urgency calls survive; the ratio lands exactly. Sanity-check that obviously-urgent issues (credential leaks, arbitrary-code-execution, crashloops, broken deploys) land in P0.

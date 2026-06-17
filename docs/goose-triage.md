# Goose issue triage

`scripts/goose-triage.py` (ward verb `goose-triage`) runs real issue triage with the local [Goose](../.agents/skills/agents-goose/SKILL.md) + `qwen3-coder:30b` harness as the judgment engine, implementing the [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) method: Python owns the deterministic parts, Goose owns the bounded per-issue judgment - "the shape a small local model can own."

**Report-only.** It never writes to issues. Apply labels yourself after reviewing the report.

## Pipeline

1. **Fetch** open issues (`coily ops forgejo issue list` + `view` for bodies).
2. **P0 net** - the regex content rules in [p0-content-rules.yaml](../.agents/skills/tooling-issue-prioritization/references/p0-content-rules.yaml) flag candidates (wide recall, deliberate over-match).
3. **P0 confirm** - one isolated Goose call per candidate: "active incident, or just discussing the topic?" This is the precision filter that the combined classifier got wrong (a design doc describing ACE must not be P0).
4. **Score the rest** - three independent Goose urgency passes on a 0-100 scale (anchored to the P1-P4 definitions, different framings), averaged. A continuous score gives the percentile cut real spread to land on. Unsure -> 30.
5. **Run-off** - qwen piles its "important" issues at a ceiling score, so any tie large enough to otherwise split arbitrarily across a tier (>= 4 members) is re-ranked against itself in one Goose call. This is what orders the top cluster by judgment instead of by issue number.
6. **Percentile cut** into the target shape (P1 10% / P2 20% / P3 30% / P4 40%), boundaries snapped to a *nearby* natural score break (the snap distance is capped, so an oversized tie is split at the target percentile rather than swallowing a whole tier). P1 floors at zero (a top-band issue is only P1 if its mean clears the absolute P1 anchor).
7. **Report** - markdown + yaml under `~/.cache/agentic-os/goose-triage/<repo>-<date>.{md,yaml}`.

The Goose calls use the anti-thrash config from the test harness: `goose run --no-profile --quiet --no-session --max-turns 1`. No extensions loaded, so the model cannot fall into tool-call looping; it answers in one turn.

## Usage

```
ward exec goose-triage -- --repo coilyco-flight-deck/agentic-os
ward exec goose-triage -- --repo <owner/name> --limit 50
```

`coily`'s issue-list verb caps at 50 with no page flag, so larger repos are fetched partially and the script warns - the percentile math is only honest over a full backlog. Paginated fetch (raw Forgejo API + an `X-Total-Count` gate, per the `tooling-triage-cascade` skill) is the next build for those.

## Production run (agentic-os, 31 issues, 2026-06-17)

Distribution: **P0 1, P1 3, P2 6, P3 9, P4 12** - the target shape, hit cleanly.

- **The tails are reliable.** P0 caught the one genuine active incident (main red, commits blocked by a hook regression). P4 correctly demoted the low-value stubs.
- **The resolution path mattered.** A first run used two tier-summing passes; 19 of 30 issues scored exactly 4/6 and the cut collapsed into P3 (61%). A 3-pass 0-100 scale fixed the gross spread (P4 4 -> 12) but exposed a ceiling cluster: 13 issues tied at 85, splitting across tiers by issue number (a LUCA-ref cleanup in P1 above a fleet-wide signing breakage in P3). The run-off fixed that - it re-ranked the 85-cluster, so P1 became the three gpg-ssm fleet-wide breakages.
- **Known limit:** qwen's per-issue scores are coarse (~25/45/65/85), so the run-off, not the raw score, does the fine ordering at the top. Over a much larger backlog the run-off groups grow and one ranking call gets less reliable - chunked or pairwise run-offs are the next lever.

## Related

- [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) - the method.
- [test-harness-goose](test-harness-goose.md) - the harness and anti-thrash config reused here.
- agentic-os#237 - heartbeat-loop follow-up.

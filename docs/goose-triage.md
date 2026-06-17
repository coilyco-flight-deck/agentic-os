# Goose issue triage

`scripts/goose-triage.py` (ward verb `goose-triage`) runs real issue triage with the local [Goose](../.agents/skills/agents-goose/SKILL.md) + `qwen3-coder:30b` harness as the judgment engine. It implements the [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) method, with Python owning the deterministic parts and Goose owning the bounded per-issue judgment - exactly the split that skill calls "the shape a small local model can own."

**Report-only.** It never writes to issues. Apply labels yourself after reviewing the report.

## Pipeline

1. **Fetch** open issues (`coily ops forgejo issue list` + `view` for bodies).
2. **P0 net** - the regex content rules in [p0-content-rules.yaml](../.agents/skills/tooling-issue-prioritization/references/p0-content-rules.yaml) flag candidates (wide recall, deliberate over-match).
3. **P0 confirm** - one isolated Goose call per candidate: "active incident, or just discussing the topic?" This is the precision filter that the combined classifier got wrong (a design doc describing ACE must not be P0).
4. **Score the rest** - two independent Goose urgency passes (different rubrics), mapped `P1=3 P2=2 P3=1 P4=0` and summed. Unsure -> P3.
5. **Percentile cut** into the target shape (P1 10% / P2 20% / P3 30% / P4 40%), boundaries snapped to natural score breaks so a run of tied scores is never split. P1 floors at zero.
6. **Report** - markdown + yaml under `~/.cache/agentic-os/goose-triage/<repo>-<date>.{md,yaml}`.

The Goose calls use the anti-thrash config from the test harness: `goose run --no-profile --quiet --no-session --max-turns 1`. No extensions are loaded, so the model cannot fall into the tool-call looping the first probe surfaced; it must answer in one turn.

## Usage

```
ward exec goose-triage -- --repo coilyco-flight-deck/agentic-os
ward exec goose-triage -- --repo <owner/name> --limit 50
```

`coily`'s issue-list verb caps at 50 with no page flag, so repos with more than 50 open issues are fetched partially and the script prints a warning - the percentile math is only honest over a full backlog. Full pagination (raw Forgejo API + an authoritative `X-Total-Count` gate, per the `tooling-triage-cascade` skill) is the next build for the large repos.

## First production run (agentic-os, 31 issues, 2026-06-17)

Distribution: **P0 1, P1 1, P2 6, P3 19, P4 4.**

- **The tails are reliable.** P0 caught the one genuine active incident (main red, all commits blocked by a hook regression). P1/P2 surfaced the real important-and-near-term work (fleet-wide signing broken, idempotency bug, rollout blockers). P4 correctly demoted the low-value stubs.
- **The middle does not differentiate.** 19 of 30 non-P0 issues scored exactly 4/6 - qwen's two-rubric scoring bunches hard at the midpoint, so the percentile cut had one giant tie block it could not spread, and P3 ballooned to 61% against a 30% target. The shape only holds when scores have spread.
- **Next lever:** finer scoring resolution - more rubrics, a forced pairwise ranking, or a wider tier-score spread - so the cut has real breaks to land on. The judgment quality is there; the resolution is not.

## Related

- [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) - the method.
- [test-harness-goose](test-harness-goose.md) - the harness and the anti-thrash config this reuses.
- [agentic-os#237](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/237) - the heartbeat-loop follow-up.

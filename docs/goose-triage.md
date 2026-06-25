# Goose issue triage

`scripts/goose-triage.py` (ward verb `goose-triage`) runs real issue triage with a **pluggable engine**, implementing the [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) method: Python owns the deterministic parts, the engine owns the per-issue judgment. The default engine is local [Goose](../.agents/skills/agents-goose/SKILL.md) + `qwen3-coder:30b`; `--engine` swaps in a stronger judge ([Engines](#engines)).

**Applies labels by default on two orthogonal axes** - the **tier** (P0-P4) and the **automation mode** (headless/interactive/consult, the eligibility filter for what `ward agent` may auto-run). Each axis converges independently, so a re-run leaves exactly one tier and one mode label. Both label sets must exist in the repo.

## Pipeline

1. **Fetch** open issues via one `ward ops forgejo issue list` call (bodies inline).
2. **P0 net** - the regex content rules in [p0-content-rules.yaml](../.agents/skills/tooling-issue-prioritization/references/p0-content-rules.yaml) flag candidates (wide recall, over-match).
3. **P0 confirm** - one judgment call per candidate: "active incident, or just discussing it?" The precision filter (a design doc is not P0).
4. **Score the rest** - three independent urgency passes on a 0-100 scale (different framings), averaged so the percentile cut has spread to land on. Unsure -> 30.
5. **Run-off** - qwen piles "important" issues at a ceiling score, so any tie >= 4 is re-ranked against itself in one call, by judgment not issue number.
6. **Percentile cut** into the target shape (P1 10% / P2 20% / P3 30% / P4 40%), snap capped so a big tie splits at the percentile rather than swallow a tier. P1 floors at 0.
7. **Mode classify** - one call per issue (P0 included) tags the automation mode, fail-closed to `consult` unless a high-confidence `headless`/`interactive`. See [automation-mode-axis](../.agents/skills/tooling-issue-prioritization/references/automation-mode-axis.md).
8. **Report** - markdown + yaml under `~/.cache/agentic-os/goose-triage/<repo>-<date>.{md,yaml}`.
9. **Apply** - write each issue's tier and mode as forgejo labels, then post one marked verdict comment (`<!-- goose-triage -->`) with both reasons, only when absent (ward-kdl has no comment-**edit** verb, so re-runs refresh labels but leave the comment). `--report-only` skips writes, `--no-comment` skips the comment.

## Engines

The judgment engine is **pluggable** behind one `ask` seam: `--engine claude` (or a `command` judge) re-triages with a stronger judge over this same scaffolding. See [triage-engines.md](triage-engines.md) for the engine list, CLI contract, and `$AOS_TRIAGE_ENGINE`.

## Forgejo access

All forgejo I/O routes through `ward ops forgejo` (ward-kdl), authenticating as the `coilyco-ops` bot from SSM - no `FORGEJO_TOKEN` ([#267](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/267), which broke the old direct-REST path). The judgment engine is separate: see [triage-engines.md](triage-engines.md) for how each engine enforces and validates its replies.

## Usage

```
ward exec goose-triage                  # current git origin; applies labels + verdict comments
ward exec goose-triage -- --report-only # produce the report, write nothing
ward exec goose-triage -- --no-comment  # apply labels but skip the verdict comments
ward exec goose-triage -- --repo <owner/name>
ward exec goose-triage -- --engine claude  # re-triage with the stronger Claude judge
```

The list verb caps at 50 per page, so larger repos fetch partially and the script warns the shape is over a partial set. Auto-pagination is tracked in ward#131.

## Related

- [triage-engines](triage-engines.md) - the pluggable judgment engines and the shared CLI contract.
- [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) - the method.
- [test-harness-goose](test-harness-goose.md) - anti-thrash config reused here.

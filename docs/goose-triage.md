# Goose issue triage

`scripts/goose-triage.py` (ward verb `goose-triage`) runs real issue triage with the local [Goose](../.agents/skills/agents-goose/SKILL.md) + `qwen3-coder:30b` harness as the judgment engine, implementing the [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) method: Python owns the deterministic parts, Goose the bounded per-issue judgment.

**Applies labels by default on two orthogonal axes** - the **tier** (P0-P4, urgency) and the **automation mode** (headless/interactive/consult). Each axis converges independently so a re-run leaves exactly one tier and one mode label per issue. Both label sets must exist in the repo. It also writes one **verdict comment** per issue carrying Goose's reason for each axis (step 9). `--report-only` skips all writes; `--no-comment` skips just the comment. The mode axis is the eligibility filter for what `ward agent` may auto-run (step 7).

## Pipeline

1. **Fetch** open issues (`coily ops forgejo issue list` + `view` for bodies).
2. **P0 net** - the regex content rules in [p0-content-rules.yaml](../.agents/skills/tooling-issue-prioritization/references/p0-content-rules.yaml) flag candidates (wide recall, deliberate over-match).
3. **P0 confirm** - one Goose call per candidate: "active incident, or just discussing it?" The precision filter (a design doc describing ACE is not P0).
4. **Score the rest** - three independent Goose urgency passes on a 0-100 scale (different framings), averaged so the percentile cut has spread to land on. Unsure -> 30.
5. **Run-off** - qwen piles "important" issues at a ceiling score, so any tie >= 4 is re-ranked against itself in one Goose call, ordering by judgment not issue number.
6. **Percentile cut** into the target shape (P1 10% / P2 20% / P3 30% / P4 40%), the snap distance capped so a big tie splits at the target percentile, not swallow a tier. P1 floors at zero.
7. **Mode classify** - one Goose call per issue (P0 included) tags the automation mode, fail-closed to `consult` unless a high-confidence `headless`/`interactive`. See [automation-mode-axis](../.agents/skills/tooling-issue-prioritization/references/automation-mode-axis.md).
8. **Report** - markdown + yaml under `~/.cache/agentic-os/goose-triage/<repo>-<date>.{md,yaml}`.
9. **Apply** - write each issue's tier and mode as forgejo labels, then upsert one marked verdict comment (`<!-- goose-triage -->`) carrying both reasons, found by marker and edited in place so a re-run updates rather than appends. `--report-only` skips all writes, `--no-comment` skips just the comment. coily's `issue comment` is add-only, so the upsert calls the forgejo API directly (coily comment verbs are a tracked follow-up).

Every judgment call goes through the `goose-json` ward verb ([`scripts/goose_json.py`](../scripts/goose_json.py)): a synthesized Goose recipe whose `response.json_schema` is the call's schema, so the provider enforces a conforming reply - no regex scraping. Calls use the anti-thrash config (`--no-profile --quiet --no-session --max-turns 1`). Each `ask()` failure is classified and buffered - see [goose-failure-records.md](goose-failure-records.md).

## Usage

```
ward exec goose-triage                          # current git origin; applies labels + verdict comments
ward exec goose-triage -- --report-only          # produce the report, write nothing
ward exec goose-triage -- --no-comment           # apply labels but skip the verdict comments
ward exec goose-triage -- --repo <owner/name>
```

`coily`'s issue-list verb caps at 50, so larger repos are fetched partially and the script warns the shape is over a partial set. Whole-backlog fetch arrives with `ward-kdl ops forgejo issue list-all` - ward#131.

## Related

- [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) - the method.
- [test-harness-goose](test-harness-goose.md) - anti-thrash config reused here.
- agentic-os#237 - heartbeat-loop follow-up.

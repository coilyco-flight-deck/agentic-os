# Phase 3 - Leverage scoring

Score the merged candidate pool and rank. The score is leverage, not novelty.

## The formula

`leverage = (value x reach x confidence) / cost`, each term 1-5, then a kind multiplier.

- **value** - how much it helps someone who has the toolset. 1 marginal, 5 transformative.
- **reach** - how many repos / people / runs it touches. A one-repo fix is low, a
  cross-repo backfill is high. Reach is usually the term that decides the ranking.
- **confidence** - how sure the build path is. A vague idea is 1, a known refactor is 5.
- **cost** - build effort in long-run units. 1 is an afternoon, 5 is multi-session.

## Kind multipliers (the defining bias)

- `backfill` x **1.5** - author once, roll across N repos. Reach is already high and the
  multiplier compounds it. This is why wide validator rollouts and config migrations win.
- `refactor` x **1.25** - improving what exists beats standing up something new of equal
  raw value, because the integration cost is already paid.
- `net-new` x **0.8** - demoted by default, and only on the board at all if it cleared
  phase 2's composition requirement. Standalone greenfield does not rank.

## Fence and dedup

- Re-apply the **reserved-surface fence** as a hard filter, in case a projected entry
  drifted onto fenced ground. Fenced means score zero, dropped, noted as fenced (not
  silently gone - log what was excluded).
- Dedup against already-open issues and against the sibling scouts' in-flight work, so the
  plan does not re-propose something already moving.

## Output

A ranked table in `YYYY-MM-DD-scout-autonomy-3-ranked.md`: rank, name, kind, the four
sub-scores, multiplier, final leverage, and one line of build path. The top 3 carry
forward to phase 4. Note any high-value entry that lost only on confidence - those are
the ones worth a quick spike to de-risk before a future run.

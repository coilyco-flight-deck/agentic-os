# Phase 4 - Contract synthesis

For the top picks, turn each ranked entry into a **long-run contract** - the artifact a
long-run execution skill consumes at the start of an overnight session. A ranked idea is
not runnable. A contract is.

Write each contract in the shape Kai's long-run discipline expects (see your
long-run execution skill). At minimum, three fields:

- **Goal** - the done-state in one or two sentences.
- **Done-condition** - the verifiable test that ends the run: tests green, the validator
  rolled to all N repos and each commit landed, the refactor merged with behavior
  unchanged. Never "when there's something to report."
- **Non-goals** - the scope fence, seeded from the run-config reserved surfaces plus
  anything this particular build should not drag in. This is what keeps the overnight run
  from wandering.

Add two fields this leg supplies that pay off downstream:

- **Build path** - the ordered first 3-5 steps, concrete enough that a long-run session
  starts without re-planning. For a backfill: author the thing, dogfood it in its home
  repo, then roll per-repo one-commit-one-push.
- **Verification hook** - how each unit self-checks before the next builds on it (the run
  command, the test, the grep). Long runs fail on confident-wrong, so name the check now.

Write contracts to `YYYY-MM-DD-scout-autonomy-4-contracts.md`, one per top pick. Each one
should be copy-paste-able as the seed of a long-run session with no further editing.

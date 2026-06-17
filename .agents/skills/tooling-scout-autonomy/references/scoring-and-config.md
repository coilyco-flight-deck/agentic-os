# Scoring weights, run-config, and cadence

## Run-config schema

Supplied at invoke, never hardcoded in this public skill:

- `repos` - the target repo list to sweep (paths or owner/repo refs).
- `notes_dir` - the notes/scratch location for phase checkpoint files.
- `reserved_surfaces` - subsystems this run must not touch or propose work on. A list of
  repo or path globs. This is the security-and-scope fence: it is how the operator keeps a
  scout off a security-boundary subsystem, a frozen API, or anything reserved. Applied at
  phase-1 intake and re-applied as a hard filter at phase 3.
- `audience` (optional) - who "people like me" are, to bias projection toward
  generalizable software over personal one-offs.

## Why the multipliers are shaped this way

The kind multipliers (`backfill` 1.5, `refactor` 1.25, `net-new` 0.8) encode one belief:
**integration cost is the hidden tax on new software, and the operator has already paid it
for everything they run.** A backfill spreads one paid integration across many repos. A
refactor improves an already-integrated thing. Net-new pays the tax again, so it must
either compose existing tools (reusing some of that paid integration) or lose. Tune the
numbers in run-config if an operator's situation differs, but keep the ordering
backfill > refactor > net-new.

## Cadence and resume

- Each phase checkpoints to `<notes_dir>/YYYY-MM-DD-scout-autonomy-{phase}.md`, so the
  operator can run "scout-autonomy phase 3" from anywhere and resume without re-running
  phase 1. The `.yaml` siblings are the machine-readable handoff between phases.
- Run this leg when the tooling surface is right but underused - capability and
  displacement have settled and the question is what to make, not what to add or shed.
- It composes the other two scouts: their outputs are phase-1 input here, and a build this
  leg ships often creates the next displacement candidate. The loop is intentional.

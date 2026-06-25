# Scrub-on-reject and notes

## Scrub-on-reject

When the user names a candidate to drop in phase 5 (or rejects one mid-install
in phase 6), do all three steps in this exact order:

1. **Scrub the candidate from phases 1-6 inbox files.** Either delete the
   line or move it to a `dropped:` section in the phase 6 file, with the
   reject reason and a date stamp.
2. **If the candidate traces back to a vault source note, ask before
   touching the source.** A candidate's `because:` rationale may cite
   user-authored notes files. Never auto-edit those.
   Surface the source line and ask whether to remove it.
3. **Record the reject reason** in the phase 6 `dropped:` section with
   the date stamp. Keep the entry visible so re-runs don't re-surface
   the same rejected candidate without context.

The order matters because step 2 is destructive against user-authored
content. The wrong default is a silent edit. Always ask.

## Notes

- **Pure-prompt skill, no script.py.** Phase 2 hydration is parsing
  enough to be a candidate for Python, but the routine is exploratory
  and judgment-heavy across phases. Migrate to Python helpers if it
  starts being run on a cadence and the hydration step ossifies.
- **Run cadence:** ad-hoc, not cron. This is a "I have an afternoon to
  expand my toolbox" routine, not a daily. Soft suggestion: roughly
  monthly. About monthly tends to align with how often new MCPs and
  skills land in the registries. Less often and the surface drifts past
  you, more often and noise drowns signal. Treat as a habit nudge, not
  enforcement.
- **Resume model:** if invoked without a phase argument, look for
  today's checkpoint files and resume from the next phase. If invoked
  with an explicit phase number, run only that phase.
- **Wrapper paths:** `ward-kdl pkg skillsmp skills {search,ai-search}`
  and `ward-kdl pkg glama server {list,get}`. These rode `coily pkg`
  until [ward#105](https://forgejo.coilysiren.me/coilyco-flight-deck/ward/issues/105)
  moved both wrappers onto the ward-kdl spec runtime (landed `ward-kdl`
  v0.58.0), retiring the coily dependency. The argv gained a resource
  layer (`skills` / `server`) and the search term is now the `--q` flag
  (positional under coily); glama directory listing paginates with
  `--after`/`--first`. Migrated 2026-06-25 (agentic-os#260).
- **Speculative entries are the point.** Don't be shy about listing
  things that don't exist yet. The "go bother someone" pathway is a
  primary use of this skill, not a side effect.

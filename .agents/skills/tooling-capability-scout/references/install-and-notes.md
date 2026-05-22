## Phase 6 - Install approved entries

For each approved entry, one issue + one commit + one push, in
the personal-OS repo (per AGENTS git workflow). Iterate sequentially, not
batched, so a failure on entry N does not block entries N+1..M.

**Skills:**

- `gh issue create -R <owner>/<personal-os-repo> --title "skill: install <name>"
  --body "<short rationale, link to source>"`. Capture the issue
  number.
- Create directory `<personal-os-repo>/.agents/skills/<name>/` and write
  `SKILL.md` (fetch from the source repo if the install method is
  copy-the-file; otherwise write a thin wrapper if the source skill is
  a plugin).
- Run `./setup.sh` from the personal-OS repo root.
- `git add` the new skill dir, commit with `closes #<issue>`, push.

**MCPs:**

- `gh issue create -R <owner>/<personal-os-repo> --title "mcp: install <name>"
  --body "<short rationale, link to source>"`. Capture the issue
  number.
- Edit `<personal-os-repo>/config/mcporter.json` to add the new server entry.
- Run `mcporter auth <name>` if OAuth is needed (the user will be prompted).
- Run `mcporter emit-ts <name> --out <personal-os-repo>/mcp-servers/<name>.d.ts
  --mode types`.
- Add a one-line entry to the `mcp-servers` skill's available servers
  list.
- `git add` mcporter.json + the new .d.ts + the mcp-servers skill edit,
  commit with `closes #<issue>`, push.

**Defense-in-depth:** before each install, re-check the entry's safety
prefix from phase 4. If it's anything other than 🟢, abort and surface
the discrepancy. Approval-by-non-denial in phase 5 is not a license to
skip the gate; the security pass is authoritative.

If an install fails (build breaks, mcporter errors, audit re-run flips
red), do not roll forward. Fix-or-skip. Document the skip in
`YYYY-MM-DD-capability-scout-6-installed.yaml` so phase 5 can be
re-run later for the holdouts.

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
- **Coily wrapper paths:** `coily pkg skillsmp` and `coily pkg glama`,
  not `coily ops`. Verified 2026-05-08.
- **Speculative entries are the point.** Don't be shy about listing
  things that don't exist yet. The "go bother someone" pathway is a
  primary use of this skill, not a side effect.

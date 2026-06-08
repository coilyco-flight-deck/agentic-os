# Phase 6 - Install approved entries

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
- Refresh the skill mount (`make refresh-symlinks`).
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

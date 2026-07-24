# Phase 6 - Install approved entries

PM does not perform this phase. PM hands each approved entry, its phase 4
evidence, and the placement recommendation to engineer. Engineer follows
`kai-git-workflow` and the target repository's resolved landing workflow.

**Skills:**

- Run the `tooling-skill-authoring` admission and placement tests.
- Choose ordinary `.agents/skills/<name>/SKILL.md` or role-scoped
  `.agents/composed/<name>/COMPOSED.md` from the intended audience.
- Preserve source provenance and copy any required resources.
- File the repository issue, validate the catalog, commit with the issue
  closure trailer, and push through the resolved workflow.

**MCPs:**

- Edit the canonical MCP inventory owned by the personal-OS layer.
- Generate or refresh any typed schema projection that inventory requires.
- Treat interactive authentication as a human checkpoint.
- File the repository issue, validate the projection, commit with the issue
  closure trailer, and push through the resolved workflow.

**Defense-in-depth:** before each install, re-check the entry's safety
prefix from phase 4. If it's anything other than 🟢, abort and surface
the discrepancy. Approval-by-non-denial in phase 5 does not bypass the
security gate.

If an install fails (build breaks, mcporter errors, audit re-run flips
red), do not roll forward. Fix-or-skip. Document the skip in
`YYYY-MM-DD-capability-scout-6-installed.yaml` so phase 5 can be
re-run later for the holdouts.

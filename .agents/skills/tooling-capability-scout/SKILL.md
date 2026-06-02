---
name: tooling-capability-scout
description: Capability gap analysis for skills and MCP servers. Sweeps repos, hydrates against skillsmp and glama, security-audits silver/gold tiers, installs one-issue-one-commit.
---

# capability-scout

## Triggers

capability scout, find me skills, find me mcps, gap analysis, missing capabilities.

Six-phase routine. Each phase runs independently and checkpoints to a
single-day vault inbox file, so the user can dictate "capability-scout phase 3"
from the train and resume without re-running phase 1.

**Why six phases:** the full pipeline is too large for one model run, and
each phase has a different cost/risk profile. Phase 1 is open-ended
ideation, phase 4 is a security gate, phase 6 mutates the user's personal-OS repo. Mixing
them into one invocation either blows context or makes the security gate
easier to skip. Splitting forces an explicit checkpoint between
"speculate" and "install."

**Outputs go to the notes/scratch location, not the personal-OS repo.** Speculative discovery
incidentally surfaces private repo intent and personal context. Only the
final per-install commits land in the personal-OS repo. Inbox path:
`<notes-dir>/YYYY-MM-DD-capability-scout-{phase}.md` (parameterize to the user's scratch/notes location).

## Phases

- [Phase 1 - Grounded sweep + speculative ideation](references/phase-1-sweep.md) - walk the working surface, build a candidate list, brainstorm what doesn't exist yet.
- [Phase 2 - Hydration](references/phase-2-hydration.md) - resolve bare names against skillsmp/glama plus an awesome-list backstop, dedup against installs.
- [Phase 3 - Categorize and rank](references/phase-3-rank.md) - semantic categories, global 3:2:1 medal ranking.
- [Phase 4 - Security audit](references/phase-4-audit.md) - 🥈/🥇 only, supply-chain-audit skill, 🟢🟡🔴 safety prefix (blocked on #185).
- [Phase 5 - Present 🥇🟢 inline](references/phase-5-present.md) - flatten the top tier to chat, explicit-deny approval.
- [Phase 6 - Install approved entries](references/phase-6-install.md) - one issue + one commit + one push per entry, defense-in-depth re-check.

## See also

- [Scrub-on-reject and notes](references/scrub-and-notes.md) - reject ordering, run cadence, resume model, coily wrapper paths, why speculative entries matter.

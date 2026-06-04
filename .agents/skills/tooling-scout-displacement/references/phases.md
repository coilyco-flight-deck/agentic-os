# scout-displacement - phases and ledger

Full per-phase routine for [tooling-scout-displacement](../SKILL.md). Read the SKILL.md
first for the pairing and the why.

## The verdict ledger

This audit recurs, so the durable output is a ledger that reruns diff against, not a
fresh report each time. Without it, every run re-discovers from zero and re-litigates
rejections. The ledger persists across runs at
`<notes-dir>/scout-displacement-ledger.md`, one record per custom subsystem:

- `custom_thing` - the subsystem, repo + path.
- `oss_candidates` - the off-the-shelf options found.
- `maturity_signals` - stars, last release, maintainer count, license.
- `verdict` - keep-custom / adopt / watch.
- `rationale` - one line, especially the why-rejected, so it is not re-debated.
- `last_evaluated` - date, so a stale watch surfaces as "re-check me."

A rerun produces a diff - new candidates, watch items that flipped to adopt, verdicts
gone stale. That diff is the deliverable. Each adopt becomes a tracking issue.

## Phases

- **Phase 1 - Inventory sweep.** Walk the target repos, build the custom-surface list: one entry per custom subsystem (repo + path, what it does, rough size / maintenance cost). This is the durable input that makes the sweep re-runnable instead of re-improvised. Granularity is a parameter - sweep per-subsystem by default, drop to per-file only where a subsystem is suspiciously large. Seed from the existing ledger so a rerun skips settled keep-custom verdicts unless they have gone stale.
- **Phase 2 - Hydration.** For each custom thing, resolve candidate OSS replacements via web search, language package registries, and an awesome-list backstop. Dedup against tools already in use. A custom thing with zero credible candidates exits here as keep-custom.
- **Phase 3 - Categorize and rank.** Group candidates by subsystem domain. Global 3:2:1 medal ranking by fit-to-need plus displacement leverage - how much custom code retires per adopted tool.
- **Phase 4 - Maturity and security audit.** 🥈/🥇 only. Verify maturity signals against primary sources (stars, release cadence, maintainer count, license compatibility), then run the supply-chain-audit skill - adopting OSS is taking on a dependency, the same gate the inbound scout applies to installs. 🟢🟡🔴 safety prefix. Sets the verdict per candidate.
- **Phase 5 - Present 🥇🟢 inline.** Flatten the top tier to chat with the displacement leverage spelled out - what retires, what it costs to migrate. Explicit-deny approval.
- **Phase 6 - Land approved entries.** One issue + one commit per adoption (the migration), and a ledger update for every watch and keep-custom verdict so the next run diffs instead of redoing. Defense-in-depth re-check before each commit.

## See also

- [SKILL.md](../SKILL.md) - the skill entry point and pairing.
- [tooling-scout-capability](../../tooling-scout-capability/SKILL.md) - the inbound sibling, same back half.

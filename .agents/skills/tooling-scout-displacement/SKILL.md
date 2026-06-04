---
name: tooling-scout-displacement
description: Outbound half of the scout pair. Build-vs-buy / NIH audit - finds custom code you maintain that off-the-shelf OSS already does, and proposes shedding it. Inventories your subsystems with code-analysis or context-as-code tooling, hydrates candidates via a targeted github search, maturity+security-audits them, lands adoptions one-issue-one-commit. Paired with tooling-scout-capability (what to ADD).
---

# scout-displacement

The **outbound** half of the scout pair. This skill answers "what custom thing do
I maintain that something off-the-shelf already does?" - your own code in, matched
to external OSS. Its sibling
[tooling-scout-capability](../tooling-scout-capability/SKILL.md) runs the opposite
direction: external catalog in, answering "what capability is missing that I should
acquire?" Same scouting instinct, inverted flow.

## Triggers

scout displacement, displacement scout, what can I replace, build vs buy, NIH audit, replace custom with OSS, what custom code can I retire.

Six-phase routine, mirroring scout-capability so the pair is one muscle. Each phase
runs independently and checkpoints to a single-day vault inbox file, so the user can
dictate "scout-displacement phase 3" from the train and resume without re-running
phase 1.

**Why six phases:** same reasoning as the inbound scout. The pipeline is too large
for one model run, and the phases have different cost/risk profiles. Phase 1 is
open-ended inventory, phase 4 is a maturity-and-security gate, phase 6 mutates a real
repo. Splitting forces an explicit checkpoint between "speculate" and "adopt."

**Outputs go to the notes/scratch location, not the personal-OS repo.** Sweeping your
own subsystems incidentally surfaces private repo intent and architecture. Only the
final per-adoption commits land in a real repo. Inbox path:
`<notes-dir>/YYYY-MM-DD-scout-displacement-{phase}.md` (parameterize to the user's
scratch/notes location).

## Phases

Full per-phase detail, the inventory tooling, and the search recipe in [references/phases.md](references/phases.md).

- **Phase 1 - Inventory sweep** - run a fixed toolchain (`scc`, `ast-grep`, `repomix`), ansible-installed, across the target repos by path.
- **Phase 2 - Hydration** - per-language github search (authority + liveness queries) for OSS that already does it, dedup against tools in use.
- **Phase 3 - Categorize and rank** - 3:2:1 medal by fit plus displacement leverage.
- **Phase 4 - Maturity and security audit** - 🥈/🥇 only, maturity signals plus supply-chain-audit.
- **Phase 5 - Present 🥇🟢 inline** - top tier to chat with leverage spelled out, explicit-deny approval.
- **Phase 6 - Land approved entries** - one issue + one commit per adoption.

## Paired with

[tooling-scout-capability](../tooling-scout-capability/SKILL.md) - the **inbound** half. The two scouts are one portfolio-management activity run in opposite directions:

- **scout-capability** - catalog in, acquire. Finds capability you lack and should add. The input is the world's skills/MCPs.
- **scout-displacement** (this skill) - inventory in, retire. Finds custom code that off-the-shelf OSS already does, and proposes shedding it. The input is your own subsystems.

Run scout-displacement when the tooling surface feels too big or too custom. Run scout-capability when it feels too small. They share the back half (research-a-candidate, security-audit, one-issue-one-commit landing) and differ only in what feeds phase 1.

## See also

- [Phases](references/phases.md) - full per-phase routine, inventory tooling, and the github search recipe.
- [tooling-scout-capability](../tooling-scout-capability/SKILL.md) - the inbound sibling.
- [tooling-supply-chain-audit](../tooling-supply-chain-audit/SKILL.md) - the phase-4 security gate, shared with the inbound scout.

---
name: tooling-scout-displacement
description: Outbound half of the scout pair. Build-vs-buy / NIH audit - finds custom code you maintain that off-the-shelf OSS already does, and proposes shedding it. Inventories your subsystems with code-analysis tooling, then hydrates OSS candidates via a per-language github search. Paired with tooling-scout-capability (what to ADD).
---

# scout-displacement

The **outbound** half of the scout pair. Answers "what custom thing do I maintain that
something off-the-shelf already does?" - your own code in, matched to external OSS. Its
sibling `tooling-scout-capability` runs the opposite direction: external catalog in,
"what capability is missing that I should acquire?"

## Triggers

scout displacement, displacement scout, what can I replace, build vs buy, NIH audit, replace custom with OSS, what custom code can I retire.

## Method

Two moves, no ceremony. Detail and the search recipe in
[references/method.md](references/method.md). Outputs go to the notes/scratch location,
not the personal-OS repo - sweeping your own subsystems surfaces private architecture,
and only an actual adoption lands a commit.

**1. Inventory the custom surface.** Run a fixed, mostly-non-overlapping toolchain
across the target repos by path, installed once via ansible so it is reproducible:
`scc` (size + COCOMO cost), `ast-grep` (structure), `repomix --compress`
(context-as-code dump). Output: one entry per custom subsystem - repo + path, what it
does, size. The target repo list is run config, not in this public skill.

**2. Hydrate OSS candidates.** For each custom thing, find OSS that already does it,
running each query once per language over `ruby, python, typescript/javascript, go,
rust` (the candidate's own language is irrelevant). Two query types: a Google
`site:github.com` authority query (README-rank surfaces the established repo) and a
GitHub-native `pushed:>` liveness query (catches newer, active libs). Dedup against
tools in use. Zero credible hits = keep-custom.

Then report per subsystem: the candidates and a fit read - adopt / partial / keep-custom
/ watch. Two cautions: adopting OSS is taking on a dependency, so sanity-check maturity
(stars, last release, maintainers, license) and run `tooling-supply-chain-audit`
before any unvetted adoption. A subsystem that is the repo's whole reason for
being usually stays custom.

When PM owns the scout, PM hands the audit and any adoption implementation to
engineer or ops. PM owns the portfolio recommendation, not dependency execution.

## Paired with

`tooling-scout-capability` is the **inbound** half. The two scouts are one
portfolio-management activity run in opposite directions:

- **scout-capability** - catalog in, acquire. Finds capability you lack and should add.
- **scout-displacement** (this skill) - inventory in, retire. Finds custom code that OSS already does, and proposes shedding it.

Run scout-displacement when the tooling surface feels too big or too custom. Run scout-capability when it feels too small.

## See also

- [references/method.md](references/method.md) - the inventory toolchain and the github search recipe.
- `tooling-scout-capability` - the inbound sibling.
- `tooling-supply-chain-audit` - the dependency-risk gate before adopting.

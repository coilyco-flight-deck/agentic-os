# scout-displacement - phases

Full per-phase routine for [tooling-scout-displacement](../SKILL.md). Read the SKILL.md
first for the pairing and the why.

## Phases

- **Phase 1 - Inventory sweep.** Run a fixed, mostly-non-overlapping toolchain across each target repo by path. Install the toolchain once via ansible (a dev-tools role) so every run is reproducible. Each tool does a distinct job - do not run interchangeable ones:
  - **scc** - per-directory LOC, complexity, and COCOMO cost estimate. The size / maintenance-cost signal that feeds displacement leverage. (one size tool, not also tokei/cloc.)
  - **ast-grep** - structural enumeration of what the code actually does, so a subsystem is identified by its logic, not just its directory. (`semgrep` only when you need rule-based depth.)
  - **repomix** (`--compress`, tree-sitter) - one context-as-code dump per repo for the boundary calls the metrics miss.

  Run by path against the configured target repos (the inclusion list is Kai-specific config, not in this public skill). Output: one inventory entry per custom subsystem - repo + path, what it does, scc size / cost.

- **Phase 2 - Hydration.** For each custom thing, find OSS that already does it. The candidate's own language is irrelevant - the best replacement may be in any of them - so run each query once per language over `ruby, python, typescript/javascript, go, rust`. Two query types:
  - **Authority query (Google):** `<what-it-does noun phrase> <language> site:github.com`, one language at a time. Google ranks by README authority, surfacing the established repo that GitHub keyword search buries.
  - **Liveness query (GitHub native):** `<capability> language:<lang> pushed:>{~12 months ago} sort:updated`, with a stars floor. Catches newer, actively-developed libraries that have not accrued authority yet.

  Dedup against tools already in use. A custom thing with zero credible hits across both query types and all languages exits as keep-custom.

- **Phase 3 - Categorize and rank.** Group candidates by subsystem domain. Global 3:2:1 medal ranking by fit-to-need plus displacement leverage - how much custom code retires per adopted tool.
- **Phase 4 - Maturity and security audit.** 🥈/🥇 only. Verify maturity signals against primary sources (stars, release cadence, maintainer count, license compatibility), then run the supply-chain-audit skill - adopting OSS is taking on a dependency, the same gate the inbound scout applies to installs. 🟢🟡🔴 safety prefix.
- **Phase 5 - Present 🥇🟢 inline.** Flatten the top tier to chat with the displacement leverage spelled out - what retires, what it costs to migrate. Explicit-deny approval.
- **Phase 6 - Land approved entries.** One issue + one commit per adoption (the migration). Defense-in-depth re-check before each commit.

## See also

- [SKILL.md](../SKILL.md) - the skill entry point and pairing.
- [tooling-scout-capability](../../tooling-scout-capability/SKILL.md) - the inbound sibling, same back half.

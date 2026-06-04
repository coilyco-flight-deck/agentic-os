# scout-displacement - phases

Full per-phase routine for [tooling-scout-displacement](../SKILL.md). Read the SKILL.md
first for the pairing and the why.

## Phases

- **Phase 1 - Inventory sweep.** Enumerate the custom surface mechanically, do not eyeball it. Two tool families, pick by what the repo needs:
  - **Conventional code analysis** - `scc` / `tokei` / `cloc` for per-directory LOC (the size signal that proxies maintenance cost and feeds displacement leverage), `universal-ctags` / `ast-grep` / `semgrep` for symbols and structure. Best when subsystem boundaries already track the directory tree.
  - **Context-as-code** - repo-to-context serializers and indexers (`repomix` with its tree-sitter `--compress`, `gitingest`, `code2prompt`, or an index like Code Context Engine). Best when boundaries are fuzzy: serialize the repo into one structured dump, then partition it into subsystems from there.

  Output: one inventory entry per custom subsystem - repo + path, what it does, LOC / rough maintenance cost. Granularity is a parameter - per-subsystem by default, drop to per-file only where one subsystem is suspiciously large.

- **Phase 2 - Hydration.** For each custom thing, find OSS that already does it with a `site:github.com` search recipe. Google ranks by README authority, so it surfaces the well-known repo that GitHub's own keyword search buries:
  - Capability query: `<what-it-does noun phrase> <language> site:github.com`
  - Curated backstop: `awesome <domain> site:github.com`
  - Anchored query, when a reference tool is known: `<known-tool> alternative site:github.com`

  Worked example - a custom pre-commit hook that validates skill frontmatter becomes `pre-commit hook validate yaml frontmatter site:github.com` plus `awesome pre-commit site:github.com`. Dedup against tools already in use. A custom thing with zero credible hits exits here as keep-custom.

- **Phase 3 - Categorize and rank.** Group candidates by subsystem domain. Global 3:2:1 medal ranking by fit-to-need plus displacement leverage - how much custom code retires per adopted tool.
- **Phase 4 - Maturity and security audit.** 🥈/🥇 only. Verify maturity signals against primary sources (stars, release cadence, maintainer count, license compatibility), then run the supply-chain-audit skill - adopting OSS is taking on a dependency, the same gate the inbound scout applies to installs. 🟢🟡🔴 safety prefix.
- **Phase 5 - Present 🥇🟢 inline.** Flatten the top tier to chat with the displacement leverage spelled out - what retires, what it costs to migrate. Explicit-deny approval.
- **Phase 6 - Land approved entries.** One issue + one commit per adoption (the migration). Defense-in-depth re-check before each commit.

## See also

- [SKILL.md](../SKILL.md) - the skill entry point and pairing.
- [tooling-scout-capability](../../tooling-scout-capability/SKILL.md) - the inbound sibling, same back half.

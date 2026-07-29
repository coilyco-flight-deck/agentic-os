# scout-displacement - toolchain and search recipe

Detail for `tooling-scout-displacement`. The skill is two moves -
inventory the custom surface, then hydrate OSS candidates. No phase ceremony.

## Inventory toolchain

Run a fixed, mostly-non-overlapping toolchain across each target repo by path. Install
once via ansible (a dev-tools role) so every run is reproducible. Each tool does a
distinct job - do not run interchangeable ones:

- **scc** - per-directory LOC, complexity, and COCOMO cost estimate. The size /
  maintenance-cost signal. (one size tool, not also tokei/cloc.)
- **ast-grep** - structural enumeration of what the code actually does, so a subsystem
  is identified by its logic, not just its directory. (`semgrep` for rule-based depth.)
- **repomix** (`--compress`, tree-sitter) - one context-as-code dump per repo for the
  boundary calls the metrics miss.

Output: one inventory entry per custom subsystem - repo + path, what it does, scc size /
cost. Granularity is a parameter - per-subsystem by default, drop to per-file only where
one subsystem is suspiciously large.

## Search recipe

For each custom thing, find OSS that already does it. The candidate's own language is
irrelevant - the best replacement may be in any - so run each query once per language
over `ruby, python, typescript/javascript, go, rust`. Two query types:

- **Authority (Google):** `<what-it-does noun phrase> <language> site:github.com`, one
  language at a time. Google ranks by README authority, surfacing the established repo
  that GitHub keyword search buries.
- **Liveness (GitHub native):** `<capability> language:<lang> pushed:>{~12 months ago}
  sort:updated`, with a stars floor. Catches newer, actively-developed libraries that
  have not accrued authority yet.

Worked example - a custom pre-commit hook that validates skill frontmatter becomes
`pre-commit hook validate yaml frontmatter site:github.com` plus the GitHub-native
`frontmatter validator language:python pushed:>2025-06 sort:updated`. Dedup against
tools already in use. A custom thing with zero credible hits exits as keep-custom.

## Acting on results

Report per subsystem: the candidates plus a fit read - adopt / partial / keep-custom /
watch. Before any adoption, verify maturity against primary sources (stars, release
cadence, maintainer count, license) and run `tooling-supply-chain-audit` - a young,
low-star tool is a real dependency risk. PM hands the audit and adoption to engineer
or ops. A subsystem that is the repo's whole reason for being usually stays custom.

## See also

- `tooling-scout-displacement` - the skill entrypoint and pairing.
- `tooling-scout-capability` - the inbound sibling.

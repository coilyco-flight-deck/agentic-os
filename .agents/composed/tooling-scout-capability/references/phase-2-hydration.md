# Phase 2 - Hydration

For each candidate from phase 1, fetch:

- Skills: `ward-kdl pkg skillsmp skills search --q <name>` and
  `ward-kdl pkg skillsmp skills ai-search --q <name>`. Take the top
  result if it's a strong match; record multiple if ambiguous.
- MCPs: `ward-kdl pkg glama server list` (paginate with
  `--after`/`--first`) and `ward-kdl pkg glama server get <namespace>
  <slug>` for exact matches.
- **Backstop:** also `WebFetch` 2-3 well-known awesome-lists
  (travisvn/awesome-claude-skills, ComposioHQ/awesome-claude-skills,
  claudefa.st's MCP list) plus the obvious first-party repo
  (`<vendor>/mcp-server-<vendor>`, `<vendor>labs/mcp`, etc.) as a
  sanity check that no established entry was missed by the registries.

**Source order depends on the category - backstop-first for infra/vendor:**

- **Well-trodden infra/vendor categories** (prometheus, grafana,
  cloudflare, aws, chrome-devtools, and similar) - hit the awesome-list
  and first-party repo backstop **FIRST**, glama second. Glama free-text
  search is recency- and spam-polluted: queries for these categories
  surface unrelated spam (SuiteCRM, DingTalk, ProposalCraft) and **miss
  the established first-party servers** (grafana/mcp-grafana,
  cloudflare/mcp-server-cloudflare, awslabs/mcp,
  ChromeDevTools/chrome-devtools-mcp). For these, the backstop is the
  primary source and glama is the supplement.
- **Niche / long-tail servers** - glama first, backstop second. Glama is
  better at surfacing the smaller, less-canonical servers that never make
  it onto an awesome-list, and the spam noise matters less when there is
  no obvious first-party answer to be drowned out.

Hydrate each into: `Org / Name / Url / Description (1 sentence)`. Keep
the original bare name in a `bare_name` field for traceability.

**Do not filter Codex/Claude/OpenCode-only entries.** the user uses all three.

If hydration fails (no match anywhere), keep the entry with
`hydration: not_found`. Speculative entries from phase 1 stay
unhydrated by definition - record them as `hydration: speculative` with
the nudge intact.

**Dedup against existing installs.** Before emitting the hydrated file,
read `<personal-os-repo>/config/mcporter.json` (existing MCP entries) and both
`<personal-os-repo>/.agents/skills/` and
`<personal-os-repo>/.agents/composed/` (existing skill sources). For each
candidate, fuzzy-match against installed names and aliases. If a probable
duplicate is found, mark the entry `dedup: existing` and include the
matched name in a `matches:` field. Dedup'd entries skip phase 4 audit
and phase 5 presentation but stay in the file for visibility (eg.
"sentry-mcp surfaced but you already have it").

Output: `YYYY-MM-DD-capability-scout-2-hydrated.yaml`.

# Phase 2 - Hydration

For each candidate from phase 1, query the native MCP catalogs first:

- **Skills:** call the SkillsMP MCP's `search_skills` tool. Try the bare
  name and one or two intent-oriented query variants, using category,
  occupation, and language filters when they narrow the result. Take the
  top result when it is a strong match and record multiple results when
  the name is ambiguous.
- **MCP servers:** call the Glama MCP's `search_server` tool, paginating
  with `after` and `first` when the result set warrants it. Call
  `get_server` for an exact namespace/slug match. Use `list_attributes`
  when Glama attributes can narrow a broad category before searching.

SkillsMP and Glama are the primary data sources for this phase. Tool
namespaces vary by harness, so select these tools from the connected
SkillsMP and Glama MCP servers rather than assuming a shell wrapper.
Do not skip the MCP pass because a category looks familiar.

After the MCP pass, cross-check:

- The obvious first-party repository (`<vendor>/mcp-server-<vendor>`,
  `<vendor>labs/mcp`, and similar) for provenance and current support.
- Two or three well-known curated lists
  (travisvn/awesome-claude-skills, ComposioHQ/awesome-claude-skills,
  claudefa.st's MCP list) as a gap-filling backstop.

These backstops verify registry results and fill holes. They never replace
the primary SkillsMP or Glama query.

For well-trodden infra and vendor categories such as Prometheus, Grafana,
Cloudflare, AWS, and Chrome DevTools, always perform the first-party
cross-check after querying Glama. Glama free-text results can be
recency- or spam-polluted and can miss an established first-party server.
For niche and long-tail servers, Glama is often the strongest discovery
surface, while the backstops may have no entry at all.

If either MCP is unavailable, record `source_status: unavailable` for that
catalog before using the configured CLI or API wrapper as a transport
fallback. A fallback does not become the primary source by substitution.

Hydrate each into: `Org / Name / Url / Description (1 sentence)`. Keep
the original bare name in a `bare_name` field for traceability.

**Do not filter Codex/Claude/OpenCode-only entries.** the human uses all three.

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

---
name: tooling-mcp-servers
description: Lazy MCP discovery via mcporter. Hard-trigger before any curl, gh, or HTTP fallback. Auto-loads Luca-stack staging (repo-recall, luca, session-lattice).
---

# mcp-servers

## Triggers

mcp, mcporter, repo-recall, luca, session-lattice, recall_search.

The lazy-loaded MCP layer. Configured servers live in `<personal-os-repo>/config/mcporter.json` (symlinked from the workspace root so `mcporter` finds them via its default `./config/mcporter.json` lookup). Typed headers per server live in `<personal-os-repo>/mcp-servers/*.d.ts`.

The point of this layout: tool schemas do not load eagerly into Claude's context. Discovery is cheap (this skill + the per-server index). Schema is paid only for the one server the agent actually needs this turn.

## Hard-trigger rule

If the agent is about to reach for **anything** that smells like an MCP-shaped capability (search a corpus, drive a browser, query an observability backend, hit a service over HTTP that has an MCP wrapper, etc.), this skill fires first. Falling back to `curl`, `gh`, raw HTTP, or "I'll just shell out" without checking the mcporter inventory is the bug. The inventory (or `mcporter list` when the inventory drifts) enumerates everything flat - read it before improvising.

## Sections

- [Auto-reach: the Luca stack (staging by default)](references/luca-stack.md) - the three implicitly in-scope servers, fuzzy aliases, prod-vs-staging, and the honeycomb note.
- [Inventorying and discovering servers](references/inventory-and-discovery.md) - inventory entry format plus `mcporter list` discovery commands and `.d.ts` regeneration.
- [Calling workflow and adding servers](references/workflow.md) - pick / read `.d.ts` / `mcporter call` / output flags, plus the add-a-server checklist.
- [Design notes](references/design-notes.md) - cross-cwd resolution, why no `.mcp.json`, and mobile / cloud MCP separation.

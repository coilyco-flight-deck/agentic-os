---
name: tooling-mcp-servers
description: Lazy MCP discovery via mcporter. Hard-trigger before any curl, gh, or HTTP fallback.
---

# mcp-servers

## Triggers

mcp, mcporter.

The lazy-loaded MCP layer. Configured servers live in `<personal-os-repo>/config/mcporter.json` (symlinked from the workspace root so `mcporter` finds them via its default `./config/mcporter.json` lookup). Typed headers per server live in `<personal-os-repo>/mcp-servers/*.d.ts`.

The point of this layout: discovery is cheap (this skill + the per-server index) and schema is paid only for the server actually needed. This is the **lazy** path - the only path on Codex, and the fallback anywhere. Note the harness split: on **Claude Code** the same merged inventory is *also* registered natively into user-scope (`mcp__<name>__*` tools) by `sync-claude-mcp.py`, since Claude's 1M window + on-demand schema deferral make native registration near-free. Both paths reach the same servers. See [Design notes](references/design-notes.md) ("Eager vs lazy is now a per-harness split").

## Hard-trigger rule

If the agent is about to reach for **anything** that smells like an MCP-shaped capability (search a corpus, drive a browser, query an observability backend, hit a service over HTTP that has an MCP wrapper, etc.), this skill fires first. Falling back to `curl`, `gh`, raw HTTP, or "I'll just shell out" without checking the mcporter inventory is the bug. The inventory (or `mcporter list` when the inventory drifts) enumerates everything flat - read it before improvising.

## Sections

- [Inventorying and discovering servers](references/inventory-and-discovery.md) - inventory entry format plus `mcporter list` discovery commands and `.d.ts` regeneration.
- [Calling workflow and adding servers](references/workflow.md) - pick / read `.d.ts` / `mcporter call` / output flags, plus the add-a-server checklist.
- [Design notes](references/design-notes.md) - cross-cwd resolution, why no `.mcp.json`, and mobile / cloud MCP separation.

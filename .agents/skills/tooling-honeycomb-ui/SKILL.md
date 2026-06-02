---
name: tooling-honeycomb-ui
description: Cookie-driven Playwright fallback for reading Honeycomb data when the official Honeycomb MCP server can't answer. Triggers - honeycomb ui scrape, honeycomb playwright, MCP fallback.
---

# tooling-honeycomb-ui

**Primary path is the Honeycomb MCP server**, not this skill. `https://mcp.honeycomb.io/mcp` is wired through mcporter as `honeycomb` (OAuth, streamable HTTP). Honeycomb Intelligence is on all plans (Free / Pro / Enterprise), so MCP works on Kai's Free account. Use `mcp__honeycomb__*` tools first.

The earlier framing that "the REST Query Data API requires Enterprise so the only programmatic path is driving the UI" conflated two separate surfaces. The `/1/query_results` REST endpoint is still Enterprise-gated, but MCP is a separate Intelligence-backed surface that doesn't go through that endpoint. Correction tracked in agentic-os-kai (see "See also").

This skill stays as the **cookie-driven Playwright fallback**: use it only when MCP can't answer a specific question that the UI can (heatmap visualization scrapes, DOM-shaped data the MCP doesn't expose, etc.).

## Procedures

- [Cookie auth handoff](references/auth-handoff.md) - why cookie-handoff over SSO-in-Playwright, plus the one-time handoff steps and `hny=` filter discipline.
- [Playwright invocation](references/playwright-invocation.md) - per-run flow: fetch cookie from SSM, inject, navigate the dataset query builder, scrape.
- [Trace-view URL surface](references/trace-view-url.md) - the `trace_id` / `fields[]` / `span=` knobs for human-readable deep links.
- [Battleships dataset reference](references/battleships-dataset.md) - the four canonical query specs for the workshop dataset.

## Boundaries

- **Cookie scope**: the session cookie is Honeycomb-scoped. It cannot reach Google, cannot mint Google tokens, cannot read mail. If the cookie leaks, rotate by signing out of Honeycomb on Kai's main browser (which invalidates server-side) and re-stashing.
- **Do not** keep a Playwright context alive across turns. Each query run opens fresh, loads cookies, runs, closes.
- **Do not** log full cookie values to chat or to scrape files. Print the rendered table or screenshot only.
- The skill is read-only against Honeycomb. Do not click Save Query / Save to Board / Trigger create buttons without explicit ask.

## See also

- `coilysiren/honeycomb-battleships/docs/reading-honeycomb.md` - workshop dataset shape and query semantics.
- `coilysiren/honeycomb-battleships/scripts/query.py` - REST Query Data API attempt, still Enterprise-gated. The MCP path supersedes this for most reads.
- `tooling-mcp-servers` → `honeycomb` entry - primary path. Run `mcporter auth honeycomb` once to mint the OAuth session.
- `tooling-claude-in-chrome` - sibling skill for the live-Chrome MCP. Use this skill instead of that one when a one-shot scrape is enough and a fresh logged-in headless context is cleaner.
- `tooling-mcp-servers` - lazy MCP resolution via mcporter; the `playwright` server is registered there.

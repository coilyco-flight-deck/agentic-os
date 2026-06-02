# Design notes: cross-cwd, no-mcp-json, mobile

## Cross-cwd resolution

mcporter layers two config sources: `<cwd>/config/mcporter.json` and the home candidate `~/.mcporter/mcporter.json`. Without the home layer, MCP calls only resolve when cwd sits inside a directory that ships its own config, so any MCP a user reaches for from `~/` or another non-config cwd is silently unreachable.

The home layer can be populated either by symlinking it at a single canonical `config/mcporter.json` (single-source setup) or by a merge script that combines multiple source configs (multi-source setup, useful when MCP entries are spread across more than one personal repo). The personal-OS repo's setup script owns whichever wire-up is in use.

## Why no `.mcp.json`

This setup replaces Claude Code's eager `.mcp.json` loading. Every tool from every configured MCP used to land in Claude's context at session start (e.g. 5 servers, 50+ tools, thousands of tokens of schema). Now: the agent sees this skill (one paragraph per server) and only pays the schema cost for the server it actually uses. The pattern is Anthropic's "code execution with MCP" idea, run through mcporter.

Trade-off: invocation goes through a shell command instead of a native tool call. Slightly higher friction per call, much lower steady-state context cost. Net win for sessions that touch zero or one MCP server (the common case).

## Mobile / cloud MCP

mcporter is local-only (Mac CLI). Anthropic-cloud connectors used by mobile Claude / claude.ai are a separate channel and are unaffected. Mobile sessions still see whatever MCPs are wired up on the cloud side. This skill is purely about Claude Code on the local host.

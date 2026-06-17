# Design notes: cross-cwd, no-mcp-json, mobile

## Cross-cwd resolution

mcporter layers two config sources: `<cwd>/config/mcporter.json` and the home candidate `~/.mcporter/mcporter.json`. Without the home layer, MCP calls only resolve when cwd sits inside a directory that ships its own config, so any MCP a user reaches for from `~/` or another non-config cwd is silently unreachable.

The home layer can be populated either by symlinking it at a single canonical `config/mcporter.json` (single-source setup) or by a merge script that combines multiple source configs (multi-source setup, useful when MCP entries are spread across more than one personal repo). The personal-OS repo's host-config convergence (ansible) owns whichever wire-up is in use.

## Eager vs lazy is now a per-harness split

The original rule here was "no `.mcp.json`, lazy through mcporter for everyone." That held when every harness paid eager `.mcp.json` schema cost up front. It no longer holds uniformly - the two harnesses now diverge:

* **Codex - lazy (unchanged).** mcporter stays the only MCP path. Invocation goes through a shell command (`mcporter call ...`) instead of a native tool call: slightly higher friction per call, much lower steady-state context cost. Net win for the common case (a session touching zero or one server) on a tighter context budget with no schema deferral.
* **Claude Code - eager (native, user scope).** Claude runs a 1M-token window *and* defers MCP tool schemas behind its own on-demand loader (the agent sees server/tool names, schema hydrates only when a tool is actually reached). So registering the whole inventory natively costs near-zero steady-state context while giving in-session, native `mcp__<name>__*` reach with no shell round-trip. `scripts/sync-claude-mcp.py` (run from the kai-config ansible role, right after the mcporter merge) registers every merged server into Claude's **user scope** via `claude mcp add-json` / `claude mcp add` - Claude Code owns the write to its own volatile `~/.claude.json`, so we don't race its rewrites. A marker file keeps it idempotent; removals from mcporter propagate as `claude mcp remove`.

This is still *not* a checked-in `.mcp.json`: user scope applies host-wide across every cwd (matching mcporter's home-layer intent) and needs no per-project approval gating. The original eager-`.mcp.json` anti-pattern - thousands of tokens of schema dumped into context at session start - stays avoided; harness schema deferral is what makes native registration cheap now. The skill inventory below still documents every server one-line either way: it is how Codex discovers them and how a Claude agent knows what a freshly-hydrated tool is for.

## Mobile / cloud MCP

mcporter is a local CLI (Mac and Linux - e.g. it drives the fleet's Linux kai-server too, not Mac-only). Anthropic-cloud connectors used by mobile Claude / claude.ai are a separate channel and are unaffected. Mobile sessions still see whatever MCPs are wired up on the cloud side. This skill is purely about Claude Code on the local host.

---
name: tooling-mcp-servers
description: Lazy MCP discovery and invocation via mcporter. Agent reads typed `.d.ts` headers per server only when needed, then calls tools through `mcporter call`. Triggers - mcp, mcporter, mcp-servers, terraform mcp, sentry mcp, playwright mcp, phoenix mcp, list mcp tools, call an mcp, what mcp servers are available, lazy mcp, code-execution-with-mcp.
---

# mcp-servers

The lazy-loaded MCP layer. Configured servers live in `<personal-os-repo>/config/mcporter.json` (symlinked from the workspace root so `mcporter` finds them via its default `./config/mcporter.json` lookup). Typed headers per server live in `<personal-os-repo>/mcp-servers/*.d.ts`.

The point of this layout: tool schemas do not load eagerly into Claude's context. Discovery is cheap (this skill + the per-server index). Schema is paid only for the one server the agent actually needs this turn.

## Inventorying servers

This skill documents the *shape* of the lazy-MCP pattern. The actual server list belongs in the personal-OS repo and changes per user. Each entry in the index should be one line: name / category / what-it-does / auth-status / `Read <path>.d.ts`. Example:

```
* terraform / registry / latest provider + module versions, capabilities, details, search modules. No auth. Read mcp-servers/terraform.d.ts.
* playwright / browser / navigate, click, fill, screenshot, network logs, evaluate JS. Local stdio via npx @playwright/mcp. Read mcp-servers/playwright.d.ts.
* phoenix / LLM observability / Phoenix traces, spans, prompts, datasets, experiments. Local stdio. Read mcp-servers/phoenix.d.ts.
* sentry / observability / issues, events, projects, orgs. OAuth completed. Read mcp-servers/sentry.d.ts.
```

## Workflow

1. **Pick the server** from the personal inventory based on the task.
2. **Read the `.d.ts`** for that server. Each tool's signature, JSDoc, and required vs optional parameters are in there. Do not skip this step. The schema is what makes the call correct.
3. **Call via `mcporter call`** with `key=value` flags or function-call syntax:
   ```bash
   mcporter call terraform.get_latest_provider_version name=aws namespace=hashicorp
   mcporter call 'phoenix.list-projects()'
   ```
   `mcporter <server>.<tool> ...` (no `call` verb) also works as shorthand.
4. **Output**: defaults to pretty text. Add `--output json` or `--raw` for machine-readable. `--json` on `list` for structured server status.

## Discovery commands (when the inventory drifts)

* `mcporter list` - all servers + tool counts + health (HTTP / auth / offline).
* `mcporter list <server>` - TypeScript-style signatures for that server's tools, inline.
* `mcporter list <server> --schema` - full JSON schema dump.
* `mcporter list --json` - structured per-server status for scripts.

When the inventory drifts from `mcporter list`, regenerate the `.d.ts` files:

```bash
cd <workspace-root>
for srv in $(mcporter list --json | jq -r '.servers[].name'); do
  mcporter emit-ts $srv --out <personal-os-repo>/mcp-servers/$srv.d.ts --mode types
done
```

Then update the inventory list.

## Adding a new MCP server

1. Add the server entry to `<personal-os-repo>/config/mcporter.json` (mirrors the old `.mcp.json` mcpServers shape, see existing entries).
2. If OAuth-protected: `mcporter auth <name>`.
3. `mcporter emit-ts <name> --out <personal-os-repo>/mcp-servers/<name>.d.ts --mode types`.
4. Add a one-line entry to the inventory.
5. Re-run the personal-OS repo's setup script so the home-layer config picks up the new server (otherwise it only resolves when cwd is inside the source repo's tree).
6. Commit (closes the same-repo issue per repo baseline).

## Cross-cwd resolution

mcporter layers two config sources: `<cwd>/config/mcporter.json` and the home candidate `~/.mcporter/mcporter.json`. Without the home layer, MCP calls only resolve when cwd sits inside a directory that ships its own config, so any MCP a user reaches for from `~/` or another non-config cwd is silently unreachable.

The home layer can be populated either by symlinking it at a single canonical `config/mcporter.json` (single-source setup) or by a merge script that combines multiple source configs (multi-source setup, useful when MCP entries are spread across more than one personal repo). The personal-OS repo's setup script owns whichever wire-up is in use.

## Why no `.mcp.json`

This setup replaces Claude Code's eager `.mcp.json` loading. Every tool from every configured MCP used to land in Claude's context at session start (e.g. 5 servers, 50+ tools, thousands of tokens of schema). Now: the agent sees this skill (one paragraph per server) and only pays the schema cost for the server it actually uses. The pattern is Anthropic's "code execution with MCP" idea, run through mcporter.

Trade-off: invocation goes through a shell command instead of a native tool call. Slightly higher friction per call, much lower steady-state context cost. Net win for sessions that touch zero or one MCP server (the common case).

## Mobile / cloud MCP

mcporter is local-only (Mac CLI). Anthropic-cloud connectors used by mobile Claude / claude.ai are a separate channel and are unaffected. Mobile sessions still see whatever MCPs are wired up on the cloud side. This skill is purely about Claude Code on the local host.

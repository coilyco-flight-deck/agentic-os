# Calling workflow and adding servers

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

## Adding a new MCP server

1. Add the server entry to `<personal-os-repo>/config/mcporter.json` (mirrors the old `.mcp.json` mcpServers shape, see existing entries).
2. If OAuth-protected: `mcporter auth <name>`.
3. `mcporter emit-ts <name> --out <personal-os-repo>/mcp-servers/<name>.d.ts --mode types`.
4. Add a one-line entry to the inventory.
5. Re-run the personal-OS repo's host-config convergence (ansible freshen) so the home-layer config picks up the new server (otherwise it only resolves when cwd is inside the source repo's tree).
6. Commit (closes the same-repo issue per repo baseline).

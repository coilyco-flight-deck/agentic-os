---
doc_goal: Define AOS-owned catalogue hydration and native MCP convergence for Agent Compose v2 consumers.
---
# AOS environment convergence

AOS owns host-aware agent inputs. `aos converge` hydrates remote skill
catalogues, emits their local manifest, and projects one mcporter inventory
into native harness configuration. Agent Compose consumes local inputs after
this boundary.

## Configuration

The default source is `~/.config/aos/converge.yaml`. An explicit `--config`
path selects another source. Relative paths resolve from its directory.
`${HOME}` and `~/` resolve against `--home` or the current user's home.

```yaml
catalogues:
  state_dir: ~/.local/state/aos
  manifest: ~/.config/aos/catalogues.json
  cache_ttl: 10m
  sources:
    - https://example.test/owner/catalogue.git/.agents/skills@main

mcp:
  inventory: ~/.config/mcporter/mcporter.json
  project_native: true
```

The sections are independent. An absent default config is an intentional
no-op. An explicitly selected missing config is an error.

## MCP contract

Canonical inventories set `imports` to an empty list. For compatibility with
older inventories, AOS treats an absent key as empty and writes an explicit
`imports: []` value into the projected inventory. Malformed or non-empty
imports remain an error. AOS always copies the safe inventory to
`~/.mcporter/mcporter.json`. With `project_native: true`, AOS also:

* replaces Claude's `mcpServers` object while preserving unrelated top-level
  configuration
* replaces AOS-managed Codex server tables while preserving unrelated tables
* expands `${HOME}` in endpoints, headers, commands, arguments, environments,
  and working directories
* maps `x-codex.defaultToolsApprovalMode` to Codex
  `default_tools_approval_mode`

Supported Codex approval modes are `auto`, `prompt`, `writes`, and `approve`.
An omitted mode leaves the default in force. The first projection absorbs the
legacy Agent Compose block. Set `project_native: false` for server-class hosts
that need only the mcporter fallback.

## Apply and check

```bash
aos converge
aos converge --check
```

Apply writes changed files atomically. `--check` performs no network access
or filesystem mutation. It exits nonzero on catalogue, manifest, or MCP drift.

## Ownership

AOS owns source selection, cache policy, host paths, MCP projection, and Codex
approval projection. Infrastructure renders host config and invokes apply or
check. Agent Compose receives the local manifest and owns role composition.

## See also

* [Catalogue cache and manifest](aos-catalogue-cache.md) - locator, refresh,
  fallback, and consumer contracts.
* [AOS launch CLI](aos-cli.md) - standalone and Ward-governed launch boundary.
* [AOS standalone connectivity](aos-standalone-connectivity.md) - ephemeral
  container inventory and tailnet bridging.
* [Ward integration boundary](ward-specs.md) - workflow ownership split.

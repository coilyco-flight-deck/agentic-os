# Features: agents and sessions

Agent naming and composition state.

## Agent self-name

Every agent session gets a stable name: `<harness>-<os>-<hostname>-<tag>-<pronouns>`, `<tag>` the last four characters of the session id and `<pronouns>` the harness's slug. The five: Claude `she-her`, Codex `he-him`, OpenCode `they-them`, Aider `they-them`, Goose `she-her`. `scripts/agent-name.sh` holds the registry and picks the harness from `AOS_AGENT_HARNESS` (default `claude`).

The claude-hooks ansible role wires Claude Code's status line and SessionStart
hook without clobbering an operator setting. Its base merge also disables
auto-memory and denies the `claude-in-chrome` computer-use MCP while preserving
other user denies. Other harnesses export `AOS_AGENT_HARNESS=<harness>` and use
the hook points they expose. Local computation stays authoritative. The fleet
permission denies and the issue-ref Stop hook it also converges are described in
[claude-settings-guardrails.md](claude-settings-guardrails.md).

### Composed status line

The [status-line composer](statusline.md) discovers ordered providers on hosts
and in dev-base containers. Its built-in provider shows the active Agent
Compose seat and bundle health. User and repository provider directories can
add, replace, or mask rows without forking the composer.

## Composed cross-harness agent context

Opt-in composer (`agent-compose`) that synthesizes global context from a declared set of sources, then points each harness's global load point (Claude Code, Codex, OpenCode) at the result by symlink. Shared sources produce one canonical `~/.config/agent-compose/COMPOSED.md` with no content duplicated on disk. A source may declare `harnesses: [claude, codex, opencode]` in YAML frontmatter when its doctrine applies only to part of the fleet. If configured harnesses select different source slices, the composer writes `COMPOSED.<harness>.md` outputs instead. Sources are listed explicitly or discovered by walking declared roots for `AGENTS.COMPOSE.md` files, the disjoint always-global doctrine that no harness's own AGENTS.md/CLAUDE.md cascade loads. A root need not be a repo checkout: pointing one at an out-of-repo directory (the ansible role uses `~/.config/agent-compose/sources/`) gives host-local doctrine a home that stays untracked and uncommitted while still composing into every harness's global context. Scope tags independently pick what composes per machine: the machine declares `scopes`, each source declares its own `scopes` in frontmatter, and a source composes only where the two sets intersect. Activation is the presence of `~/.config/agent-compose/agent-compose.yaml`: with no config, the composer is a total no-op and every harness behaves exactly as it does without it. The agent-compose ansible role runs it idempotently on each host.

A missing source degrades rather than freezes: Agent Compose skips it with a
warning and composes from the rest, while still refusing an empty result.
Infrastructure convergence and bare `acompose` refresh the load points through
the Go product. AOS ships no second composer or SessionStart refresh hook.

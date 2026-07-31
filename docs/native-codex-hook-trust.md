# Native Codex hook trust

Assigned `acompose <role> codex` launches persist trust for the converged native
Git attribution hook. This removes the repeated `/hooks` review after a new or
changed attribution definition while keeping trust scoped to that one hook.

## Trust flow

AOS starts Codex app-server over its local standard-input transport and uses
the supported `hooks/list` method. A hook qualifies only when all of these
properties match:

* the source is the user's `~/.codex/hooks.json`
* the event is `PreToolUse` with the `Bash` matcher
* the handler is an enabled, non-managed command
* the command exactly matches the converged `agent-git-attribution` path

For an untrusted or modified match, AOS writes Codex's reported hook key and
current hash through `config/batchWrite`. The `hooks.state` edit uses an upsert,
so unrelated trust entries remain unchanged. An already trusted definition
needs no write.

Missing Codex and missing attribution hooks are no-ops. App-server failures
produce a launch warning and preserve Codex's normal interactive review path.
AOS never uses `--dangerously-bypass-hook-trust` or edits Codex's private state
directly.

## Scope

This behavior runs only for caller-assigned Codex launches through `acompose`.
Bare native harness launches retain their existing trust behavior. A changed
attribution definition receives its new current hash on the next assigned
launch.

## See also

* [Native agent workspaces](native-agent-workspaces.md) - workspace and shadow-home lifecycle.
* [Agents and sessions](features-agents-sessions.md) - surrounding native harness policy.

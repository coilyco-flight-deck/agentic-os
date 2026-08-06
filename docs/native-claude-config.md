# Claude configuration projection

A native session home projects host configuration into
[an isolated workspace](native-agent-workspaces.md). Claude Code needs one step
beyond the ordinary symlink farm, because its config file sits outside the
directory the session projects.

## The asymmetry with Codex

Codex reads `config.toml` from inside `$CODEX_HOME`, so the session's `.codex`
symlink carries it whole. Claude Code reads `.claude.json` from
`$CLAUDE_CONFIG_DIR`, while most installs keep that file at the home root, one
level above the projected `.claude` directory. Staging `.claude` alone
therefore leaves the harness pointed at a path that holds nothing.

Without the link, the session starts on an empty config. It loses folder trust,
the entire MCP server registry, and every recorded onboarding and permission
decision, while the harness reports no error. The MCP projection writes the
host file, so an unlinked session also reads a registry nothing updates.

## What the launcher does

The session home links the host config into its `.claude` directory. One
resolver owns the config-location question for the whole CLI, preferring the
`$CLAUDE_CONFIG_DIR` spelling when it exists and falling back to the home root.
Both the MCP projection and the session staging resolve through it, so
projection and consumption cannot drift apart.

A standalone home copies rather than links, keeping its sealed boundary. It
receives its own config inside `.claude` instead of a view of the host file.

## Folder trust

Trust is keyed by absolute project path, and every session mints a fresh
workspace path, so an accepted dialog never carries forward on its own. The
launcher pre-accepts the paths it just created before the harness starts.

Each path is seeded in both its raw and its symlink-resolved spelling, because
macOS resolves `/var` to `/private/var` and the harness records whichever form
it was launched with. Writers resolve the link before an atomic rename, so the
session keeps a symlink to the host file rather than a divergent copy.

Seeding failure is reported and never blocks a launch. Trust is a convenience,
and a session that prompts is still a working session.

## Credentials

The config link carries onboarding and registry state, not the login itself. On
macOS the OAuth token lives in the Keychain under a service name keyed to
`CLAUDE_CONFIG_DIR`, so a session-scoped config directory never finds it. See
[Claude credential bridging](native-claude-credentials.md).

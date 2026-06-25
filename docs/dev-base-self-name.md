# In-container agent self-name

A host session self-names through a Claude Code SessionStart + statusLine hook
the claude-hooks ansible role wires into `~/.claude/settings.json`. That role
never runs inside a `ward agent` container, so a warded explorer / headless
agent in the [dev-base image](dev-base-image.md) used to stay nameless
([agentic-os#281](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/281)).
The image bakes the self-name slice in directly.

## What the image bakes

- [`agent-name.sh`](../docker/dev-base/agent-name.sh) - a trimmed sibling of the
  host [`scripts/agent-name.sh`](../scripts/agent-name.sh), landed world-readable
  at `/opt/agentic-os/agent-name.sh` so it runs as any uid. Its name-derivation
  block is format-identical to the host script (same
  `<harness>-<os>-<host>-<tag>-<pronouns>` shape, same harness registry keyed on
  `AOS_AGENT_HARNESS`). Only the host-only statusline flavor is dropped: the
  context-usage snippet, the project-local second row, `$AGENT_STATUSLINE_EXTRA`,
  and the `ward agent-name` override probe. In a container `<os>` resolves to
  `linux` and `<host>` to the container hostname, so the name encodes *which*
  explorer is which - useful for telling concurrent warded agents apart in logs,
  issue-comment signoffs, and o2r channel traffic.
- [`managed-settings.json`](../docker/dev-base/claude-managed-settings.json) -
  landed at the fixed `/etc/claude-code/managed-settings.json`. It adds only a
  `statusLine` and a `SessionStart` self-name hook, both pointing at the baked
  script.

## Why policy-tier settings

The image bakes in no user: ward owns the run-as-uid, mount set, and config
injection. Policy settings are the one Claude Code surface whose location does
not depend on the run-as-uid, `HOME`, or `CLAUDE_CONFIG_DIR` ward picks, so a
fixed `/etc/claude-code/managed-settings.json` reaches the agent regardless. It
adds only the two self-name keys, so it layers over whatever ward injects into
user settings rather than replacing it.

## Drift

Like the [substrate seed](dev-base-image.md), `agent-name.sh` is a denormalized
copy kept in the build context. Its name-derivation block must stay
format-identical to the canonical host [`scripts/agent-name.sh`](../scripts/agent-name.sh):
the matching name is the contract this feature exists to honor.

## See also

- [docs/dev-base-image.md](dev-base-image.md) - the image this rides in.
- [docs/features-agents-sessions.md](features-agents-sessions.md) - the host self-name feature.
- [docs/FEATURES.md](FEATURES.md) - feature inventory.

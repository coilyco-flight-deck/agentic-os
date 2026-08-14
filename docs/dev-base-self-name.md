# In-container agent self-name

A host session self-names through a Claude Code SessionStart + statusLine hook
the claude-hooks ansible role wires into `~/.claude/settings.json`. That role
never runs inside a `ward agent` container, so a warded explorer / headless
agent in the [dev-base image](dev-base-image.md) would otherwise stay nameless.
The image bakes the same slice in directly.

## Agent Compose owns the name

The name comes from `acompose whoami`, which prints the composed seat and the
session short id (`Angie [she] uz86`). Nothing derives a name locally.

That is the change worth knowing about. The retired `agent-name.sh` computed a
name from harness, OS, hostname, and a tag sliced out of the raw session UUID.
It could not know the composed seat, so an agent introduced itself as one thing
while its status line said another, and the tag used the full alphabet rather
than the [dictatable](https://forgejo.coilysiren.me/coilyco-flight-deck/agent-compose/src/branch/main/docs/short-id.md)
one, so it was not reliably speakable.

It also had to exist twice - a host copy and a format-identical container copy -
with a documented drift hazard between them. There is now one script and one
authority.

## What the image bakes

- [`session-name.sh`](../docker/dev-base/session-name.sh) - the SessionStart
  banner, landed world-readable at `/opt/agentic-os/session-name.sh` so it runs
  as any uid. It reads the project directory from the hook payload, calls
  `acompose whoami`, and prints nothing when there is no projection or no
  `acompose` on PATH. The same file is what the host wires, so the two surfaces
  cannot drift.
- [`git-identity.sh`](../docker/dev-base/git-identity.sh) - the
  [git-identity stamp](dev-base-git-identity.md), split out because it never had
  anything to do with naming beyond sharing a hook event.
- [`statusline.d/20-container.sh`](../docker/dev-base/statusline.d/20-container.sh) -
  a [status-line](statusline.md) row naming the warded container from
  `WARD_CONTAINER_NAME`, since inside a container the hostname is an opaque id.
  It self-suppresses on a native host.
- [`managed-settings.json`](../docker/dev-base/claude-managed-settings.json) -
  landed at the fixed `/etc/claude-code/managed-settings.json`, adding the
  `statusLine` composer and the two `SessionStart` hooks.

## Why policy-tier settings

The image bakes in no user: ward owns the run-as-uid, mount set, and config
injection. Policy settings are the one Claude Code surface whose location does
not depend on the run-as-uid, `HOME`, or `CLAUDE_CONFIG_DIR` ward picks, so a
fixed `/etc/claude-code/managed-settings.json` reaches the agent regardless. It
adds only those keys, so it layers over whatever ward injects into user settings
rather than replacing it.

## See also

- [docs/statusline.md](statusline.md) - the composer that mounts these rows.
- [docs/dev-base-git-identity.md](dev-base-git-identity.md) - the git-identity stamp.
- [docs/dev-base-image.md](dev-base-image.md) - the image this rides in.
- [docs/features-agents-sessions.md](features-agents-sessions.md) - the host feature.
- [docs/FEATURES.md](FEATURES.md) - feature inventory.

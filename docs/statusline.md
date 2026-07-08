# Status-line composer

A provider-discovery framework that auto-mounts the **full segment-composed
status line** into every warded container, so an in-container agent session
shows the same multi-row line a host session does - not just the agent-name row
See docs/dev-base-self-name.md.

## The problem it replaces

The host [`scripts/agent-name.sh`](../scripts/agent-name.sh) hand-wired the
second row: it ran `$project_dir/.agentic-os/statusline.sh` and
`$AGENT_STATUSLINE_EXTRA` and appended their output. The container copy did not,
and `statusline.sh` was never shipped into the [dev-base image](dev-base-image.md),
so everything past the name row was absent in containers. Adding each segment by
hand does not scale and forces external users to fork the composer to customize.

## How it works

A **composer** ([`docker/dev-base/statusline.sh`](../docker/dev-base/statusline.sh))
is Claude Code's `statusLine` command. It reads the `statusLine` JSON payload on
stdin, runs each discovered **provider** in filename order (handing it the same
payload on stdin), and joins their output into the multi-row line.

**Provider contract:** exit 0 with stdout = that segment; empty stdout or a
non-zero exit = skipped. So a segment **self-suppresses** when irrelevant - the
[repo-tracker](repo-tracker.md) renders nothing in a single-clone container,
where its scan root does not exist.

The two existing segments are now providers: agent-name -> `10-agent-name.sh`
(a shim delegating to the sibling [`agent-name.sh`](dev-base-self-name.md)
statusline mode), repo-tracker -> `20-repos.sh`.

## Discovery and overlays

The composer walks three provider dirs, lowest precedence first:

1. **base** - `<composer-dir>/statusline.d` (baked into the image; override with `AOS_STATUSLINE_DIR`).
2. **user** - `${XDG_CONFIG_HOME:-$HOME/.config}/agentic-os/statusline.d`.
3. **repo** - `<project_dir>/.agentic-os/statusline.d`.

A same-named file in a higher dir **overrides** the lower one; a new `NN-*.sh`
**adds** a row. A shadowing file that is not executable **masks** the lower
provider. So a project or an external user customizes the line by dropping in a
provider - **no fork** of the composer. Use 2-digit prefixes (lexical sort puts
`100` before `20`).

## Why it auto-mounts everywhere

Every warded container runs dev-base, and the baked policy-tier
[`managed-settings.json`](dev-base-self-name.md) points `statusLine` at the
composer. ward injects no `statusLine` of its own, so the baked one is
authoritative. A new base provider rides the next image build to **all**
containers at once, with no per-container or per-host edit. Per doctrine the host
rollout (the claude-hooks ansible role pointing the host `statusLine` at this
composer) lands in infrastructure/ansible; the composer and providers authored
here are host-portable so host and container stay format-identical.

## See also

- [docs/dev-base-self-name.md](dev-base-self-name.md) - the agent self-name segment + the baked managed settings.
- [docs/repo-tracker.md](repo-tracker.md) - the `20-repos` provider.
- [docs/features-agents-sessions.md](features-agents-sessions.md) - the host self-name feature.
- [docs/dev-base-image.md](dev-base-image.md) - the image this rides in.
- [docs/FEATURES.md](FEATURES.md) - feature inventory.

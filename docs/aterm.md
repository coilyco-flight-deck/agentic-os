# The native agent terminal

Two things decide what a native agent session looks like: `aterm`, which opens the window, and the status-line composer, which fills the rows inside it.

## `aterm`

`aterm` opens one composed agent session in its own branded kitty window. It is the windowed sibling of the `acompose` shell function, runs the same runtime of a leased shadow wrapping `agent-compose launch`, and leaves the terminal you typed in free. Name a role without a seat and both take the agent from [`harness-launch-profiles.yaml`](../.agents/harness-launch-profiles.yaml), which `aos` owns and both ask, so neither carries a second parser.

```text
aterm                              # pick a role, then a seat
aterm platform                     # the role's default seat
aterm platform codex -- --resume   # arguments for the harness
aterm --list                       # the live roster, no window
```

It needs `agent-compose` and kitty on `PATH` and bundles neither. Without `aos` it still launches, unleased. `--dry-run` prints the plan and opens nothing.

**It refuses a stale role before it opens anything.** Role slugs turn over, so
`aterm` reads `agent-compose catalog roles --json` on every run and names the live roster in the refusal. A transposed `platform` comes back as `is not a live role. Did you mean platform?` plus every live slug and display name. A seat is checked twice: it has to belong to the role, and to be a harness `agent-compose launch` can start. A catalogue seat like `penpot` is real but not launchable, and the refusal says which of the two it failed.

**Tab completes from the same roster.** `aterm <TAB>` offers the live slugs,
`aterm sysadmin <TAB>` only that role's launchable seats, so a slug that turned over stops completing rather than completing into a refusal. The read is under 10ms, so no cache can go stale. `shell/common.sh` registers bash and zsh through `aterm completion <shell>`, after `compinit` in zsh. A missing `agent-compose` yields silence, never a diagnostic mid-keystroke.

**A slow pre-flight names itself.** `aterm` shells out for a seat, roster, and
overlay before it opens anything, and captures their output, so a wrapped `aos` converging the host first presented as a launcher that had stopped. After two seconds `aterm` names the command it waits on.

**A failing launch stays on screen.** A terminal closes the window the moment its
child exits, so a failed launch used to vanish before anyone could read why. `aterm` runs the child through its own `_session` stage rather than handing the harness to kitty directly. That stage passes the exit code through and holds the window on any non-zero exit, and `--hold` also holds after a clean exit. The launcher watches for a startup failure, so "no window appeared" names its cause.

**The title leads with what separates two windows.** A window manager truncates near 30 characters, so the segments run workspace, task title, role, glyphs and seat name, expression. The workspace is the checkout `--working-directory` points at, rendered `repo@branch`, and it is left out rather than printed as a constant when the directory is the default projects root. Two `aterm platform` windows in different checkouts used to produce byte-identical titles.

**It decodes the whole identity overlay.** `agent-compose overlay --json` ships a complete sensory identity per personality, and a Go struct that names fewer fields drops the rest in silence. `aterm/overlay.go` declares every leaf the overlay ships: `seat.key` and `seat.tier`, the personality's `name`, `color`, and `motif`, `emblem{name,emoji,glyph}`, `form{silhouette,geometry,motion}`, and `sound_mark{timbre,contour,pulse}`. Only the glyphs and `favorite_color` reach the window today, and the rest is decoded because the identity card, the launch motion, and the sound mark are built from it. `TestOverlayDecodesEveryShippedField` round-trips each fixture through the struct and fails on any leaf that does not come back.

## Status-line composer

A provider-discovery framework that auto-mounts the **full segment-composed status line** into every warded container, so an in-container agent session shows the same line a host session does.

## The problem it replaces

The retired host `agent-name.sh` hand-wired the second row from `$project_dir/.agentic-os/statusline.sh` and `$AGENT_STATUSLINE_EXTRA`. The container copy did not, and `statusline.sh` never shipped into the [dev-base image](dev-base-image.md), so everything past the name row was absent in containers. Hand-adding each segment does not scale, and it forces an external user to fork the composer to customize.

## How it works

A **composer** ([`docker/dev-base/statusline.sh`](../docker/dev-base/statusline.sh)) is Claude Code's `statusLine` command. It reads the `statusLine` JSON payload on stdin, runs each discovered **provider** in filename order (handing it the same payload on stdin), and joins their output into the multi-row line.

**Provider contract:** exit 0 with stdout = that segment; empty stdout or a
non-zero exit = skipped. So a segment **self-suppresses** when irrelevant - the Agent Compose provider renders nothing outside a projected workspace, or where `acompose` is absent.

The built-in provider is:

* `15-agent-compose.sh` - asks `acompose statusline` to render the immutable
bundle identity, role and harness, selected catalog footprint, and composition health.
* `20-container.sh` - names the warded container from `WARD_CONTAINER_NAME`,
since inside a container the hostname is an opaque id. Silent on a host.

Two earlier base providers were removed. `10-agent-name.sh` duplicated the identity `acompose statusline` already renders, and `20-repos.sh` rendered a stray-checkout count, which is residency scanning rather than session state. `agent-name.sh` itself is retired: the [SessionStart banner](dev-base-agent-identity.md) reads `acompose whoami`.

Agent Compose owns the row's content and bundle semantics. AOS only discovers the provider and passes the project directory, so the status line does not grow a second projection parser or identity cache.

## Discovery and overlays

The composer walks three provider dirs, lowest precedence first:

1. **base** - `<composer-dir>/statusline.d` (baked into the image; override with `AOS_STATUSLINE_DIR`).
2. **user** - `${XDG_CONFIG_HOME:-$HOME/.config}/agentic-os/statusline.d`.
3. **repo** - `<project_dir>/.agentic-os/statusline.d`.

A same-named file in a higher dir **overrides** the lower one, a new `NN-*.sh`
**adds** a row, and a shadowing file that is not executable **masks** the lower
provider. So a project or an external user customizes the line by dropping in a provider, **no fork** of the composer. Use 2-digit prefixes (lexical sort puts `100` before `20`).

## Why it auto-mounts everywhere

Every warded container runs dev-base, and the baked policy-tier [`managed-settings.json`](dev-base-agent-identity.md) points `statusLine` at the composer. ward injects no `statusLine` of its own, so the baked one is authoritative, and a new base provider rides the next image build to **all** containers at once. On hosts, `install-session-name.py` migrates a legacy direct self-name command to this composer and repoints a SessionStart hook still wired to the retired `agent-name.sh`. The infrastructure claude-hooks role invokes that installer, keeping rollout separate from the provider authored here.

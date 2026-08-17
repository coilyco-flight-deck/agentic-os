# Terminal host setup

Per-host install and channel layout for Warp. The module model (apply/doctor, state layers, paths) lives in [warp.md](warp.md).

## Channels

Two Warp channels coexist on the Mac daily driver with separate bundle ids, URL schemes, and config dirs. Preview is the default-clicked terminal, Stable the named fallback.

- **Preview** (daily driver) - `/Applications/WarpPreview.app`, bundle `dev.warp.Warp-Preview`, scheme `warppreview://`, config dir `~/.warp-preview/`. Install: `ward pkg brew install --cask warp@preview --allow-untapped`.
- **Stable** (fallback) - `/Applications/Warp.app`, bundle `dev.warp.Warp-Stable`, scheme `warp://`, config dir `~/.warp/`. Install: `ward pkg brew install --cask warp --allow-untapped`.

Windows mirrors the split: Preview installs to `%LOCALAPPDATA%\Programs\WarpPreview` with config under `%LOCALAPPDATA%\warp\WarpPreview\`, Stable to `%LOCALAPPDATA%\Programs\Warp` with config under `%LOCALAPPDATA%\warp\Warp\`. `apply`/`doctor` auto-detect by install dir, preferring Preview, same as the Mac.

URL schemes are channel-specific by design: `warp://` always lands in Stable, `warppreview://` in Preview. There is no LaunchServices "default Warp" toggle that flips this, so tooling picks the channel by scheme at the call site.

Preview auto-symlinks `launch_configurations`, `tab_configs`, and `themes` into `~/.warp/` on first launch, so checked-in configs cover both channels for free. `settings.toml` is the one file that does not auto-share, so the dual-channel install points Preview's at the same source as Stable's.

## Install playbook (Mac daily driver)

Install the Preview cask, launch it once so it creates `~/.warp-preview/` and
symlinks the shared subdirs, then replace its `settings.toml` with a symlink to
this repo's copy. Run `scripts/set-warp-default-editor.sh` to bind file-type
defaults to Preview, honoring `WARP_DEFAULT_EDITOR_BUNDLE_ID` and
`WARP_DEFAULT_EDITOR_APP_PATH` for per-host overrides. Pin WarpPreview in the
Dock and unpin Warp.

Then `just warp apply` reconciles settings, theme, launch configs, and
SQLite.

When a Preview regression breaks a workday:

- `open -a Warp` opens Stable by bundle name.
- `warp://` URIs always route to Stable - useful for known-good URI tests.
- `just warp apply --channel stable` reconciles Stable's `~/.warp/` config and `dev.warp.Warp-Stable` SQLite directly (or export `WARP_CHANNEL=stable`). Without it, apply/doctor auto-detect and prefer Preview.
- `ward pkg brew upgrade --cask warp@preview --allow-untapped` picks up the next Preview release. Warp ships weekly.

- `launch_configurations/` - one window, one-or-more tabs per YAML. URI `warppreview://launch/<name>`. `apply` symlinks each into the config dir and sweeps dangling links.
- `tab_configs/` - one tab per TOML, opens in the active window. URI `warppreview://tab_config/<name>`. The tab_config URI handler landed in Warp builds dated 2026-05-15 or later.
- `themes/` - color theme YAML files.
- `scripts/` - host-side helpers (`set-warp-default-editor.sh`).
- `settings.toml` - top-level settings, symlinked into both channels' config dirs.
## Mouse-tracking escape hatch

A child under a warded director (a WSL tool, an Ink CLI) can enable xterm
mouse-tracking mode 1003 and exit without restoring it, flooding the pane with
raw `^[[<35;X;YM` SGR motion reports that nothing consumes.

A prompt-level reset cannot heal it. Mode 1003 is emulator state, cleared only
when a process writes DECRST into the output stream, which a shell does when it
draws a prompt. While the director TUI holds the terminal no prompting shell
runs, so the outer prompt fires only once the director exits, which is why the
historical answer was "drop the TUI." An inner precmd hook fails the same way,
and a keybinding that sends text writes the director's stdin.

So `warp apply` renders `keybindings.yaml` beside `settings.toml` with one
managed binding, `workspace:toggle_mouse_reporting` on `ctrl-shift-m`. It flips
mouse reporting at the **emulator layer** with no cooperation from the director
or any child, so one press stops the flood with the TUI still running. It is a
toggle rather than a one-way disable, which is fine for an escape hatch, and it
rides `warp apply` and `warp doctor` to every host.

The genuinely correct fix is upstream, in the director TUI re-asserting mouse
state on redraw, and is not ours to patch. A dev-base `BASH_ENV` self-heal was
investigated and deferred: it must emit to `/dev/tty` guarded by `[ -t 1 ]` to
avoid injecting escapes into captured output fleet-wide, and that guard may mean
it never fires for the pipe-backed children that matter.

## Branded Alacritty directors

`aosterm` launches one composed session in one statically branded Alacritty
window. Agent-compose supplies canonical identity, agentic-os renders the
terminal brand, and `aoscompose` remains the child process. `agent-terminal`
stays as the compatibility command name.

## Base configuration

[`alacritty/alacritty.toml`](../alacritty/alacritty.toml) carries the portable
Sombra palette, opaque window treatment, padding, font size, live reload, and
copy-only OSC 52 policy, leaving shell selection, startup directory, and
scrollback to the host, and defining no tabs, panes, or multiplexer. A
host-local root config imports this baseline and adds only its shell and
startup directory.

## Launch

`aosterm` is the repository-scoped entry point, taking `--expression`,
`--task-title`, `--working-directory`, then a role, a seat, and an executable
tail. Installation, upgrades, rollbacks, and version checks are in the
[native launcher walkthrough](agent-terminal-native.md).

`--working-directory` defaults to `$PROJECTS_ROOT`, with `~/projects` as the
portable fallback, and a caller passes it explicitly to open one director
inside a specific checkout.

The launcher calls `agent-compose overlay --json`, validates it, then launches
Alacritty with `aoscompose <role> <seat> ...` as its tail. It derives a title
from personality glyphs, the seat annotation, expression, and task, plus the
melded favorite color as cursor and selection accent, a subtle background tint,
and selection text chosen by contrast. The annotation is the overlay's composed
`annotation` field, so the title matches every other agent surface.

Every value reaches Alacritty as an argument. The launcher invokes no shell and
emits no terminal control sequences into the director process.

## Inspect

`--dry-run` before the `aoscompose` arguments prints `agent-terminal.launch.v1`
JSON without requiring Alacritty, carrying the selected identity, derived brand,
working directory, and complete argument vector. `AGENT_COMPOSE_BIN`,
`AOSCOMPOSE_BIN`, and `ALACRITTY_BIN` select non-default executables.

## Ownership and limits

Agent-compose owns renderer-neutral identity and validates role, seat, and
expression. Agentic-os owns this Alacritty adapter, Ward owns runtime authority
and the director lifecycle, and infrastructure owns fleet installation.

Branding is fixed at launch. The adapter manages no tabs, panes, sessions,
avatars, or interactive loop, and does not remap the ANSI palette because
director TUIs use those colors semantically.

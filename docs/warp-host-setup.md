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

## Branded kitty sessions

`aterm` opens one composed agent session in one statically branded kitty
window. Agent-compose supplies canonical identity and the roster, agentic-os
renders the terminal brand, and the native session shadow runs the harness. The
launcher, its refusals, and its flags are in
[the native agent terminal](aterm.md).

## Base configuration

[`kitty/kitty.conf`](../kitty/kitty.conf) carries the portable Sombra palette,
opaque window treatment, padding, font size, and copy-only clipboard policy,
leaving shell selection, startup directory, and scrollback to the host, and
defining no tabs, panes, or multiplexer. A host-local root config includes this
baseline and adds only its shell and startup directory.

kitty has its own tab surface, so hiding the bar is not enough on its own. The
shortcuts still exist and would silently split an agent session's window, so
each one is unmapped rather than left to a hidden bar.

[`alacritty/alacritty.toml`](../alacritty/alacritty.toml) carries the same
baseline for Alacritty and is retained for Windows, where kitty does not ship.
Pointing `--terminal-bin` at Alacritty there needs its own flag dialect, which
is not built. Tracked in [aterm's terminal showdown](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/1264).

## Ownership and limits

Agent-compose owns renderer-neutral identity and the roster it is validated
against. Agentic-os owns this kitty adapter, Ward owns runtime authority and
the session lifecycle, and infrastructure owns fleet installation.

Branding is fixed at launch. The adapter manages no tabs, panes, sessions,
avatars, or interactive loop, and does not remap the ANSI palette because
harness TUIs use those colors semantically.

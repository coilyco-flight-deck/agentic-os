# Warp config module

The `warp/` Go module establishes and verifies Kai's Warp terminal config across hosts. Run it through ward, never bare `go`:

- `ward exec warp apply` - host-aware, idempotent: reconcile every state layer.
- `ward exec warp doctor` - verify only: PASS/FAIL per check, no mutation.

The repo is the source of truth. `apply` pushes the repo's intent onto the host, `doctor` reports drift without touching anything. Both resolve the repo root by walking up from cwd to the first `.git`, so they work from any subdir and adapt automatically when the checkout moves.

## State layers

`apply` reconciles four kinds of state, each with a matching `doctor` check:

- **Rendered files** - `settings.toml`, the theme YAML, `tab_configs/startup_config.toml`. Embedded templates rendered to real files (not symlinks) in the Warp config dir. Drift = content mismatch.
- **Launch-config symlinks** - every `warp/launch_configurations/*.yaml` is symlinked into the config dir's `launch_configurations/`, and dangling links are swept. See [launch configs](#launch-configs) below.
- **SQLite settings** - keys in Warp's `warp.sqlite` that have no TOML surface (see `mapping.go`). Skipped until Warp has initialized the DB once.
- **Wallpaper** - existence check only.

## Per-OS config dir

`paths.go` resolves the layout per OS. The config dir is:

- **macOS** - channel-aware. Preview (default) at `~/.warp-preview/` with SQLite under `dev.warp.Warp-Preview`, Stable (fallback) at `~/.warp/` with SQLite under `dev.warp.Warp-Stable`. The config dir and SQLite bundle are always a matched pair (see below).
- **Windows** - channel-aware: `%LOCALAPPDATA%\warp\WarpPreview\` or `...\warp\Warp\`, config in `<channel>\config\`, SQLite in `<channel>\data\`. Themes scan `%APPDATA%` (Roaming), same split.
- **Linux** - `~/.config/warp-terminal/`.

On macOS and Windows the two channels coexist, so `apply`/`doctor` pick one and target its config dir and SQLite together. Selection: `--channel preview|stable` (or `WARP_CHANNEL` env) wins, else auto-detect by installed app (macOS `/Applications`, Windows `%LOCALAPPDATA%\Programs`), **preferring Preview**. The resolved channel is echoed in the header line (`darwin host (warp preview)`). Linux is single-channel and ignores the flag.

`WorkspaceDir` is the parent of the repo root. `StartupDir` (where a fresh tab opens) is one level above that on every OS.

## Launch configs

Launch configs are mirrored, not rendered: the repo dir is the source, the config dir holds a symlink per `*.yaml`. `apply` creates any missing link, repoints a stale one, and sweeps links that no longer resolve. It is idempotent - a link already pointing at the right source is left alone - and it never touches real files or healthy unrelated links. A pre-existing real file at a target is backed up to `<name>.bak` before linking.

This walk exists because the links used to be hand-made and orphaned, so a new launch config (or a moved checkout) stayed invisible to Warp until someone ran `ln -s` by hand. Implementation in `launch.go`.

`tab_configs/` entries beyond the rendered `startup_config.toml` remain hand-placed real files, not part of this walk.

## Sharp edges

- **Preview vs Stable** - two channels coexist with separate config dirs and URL schemes. `warppreview://` always lands in Preview, `warp://` in Stable. See [warp-host-setup.md](warp-host-setup.md) for the channel split and install playbook.
- **SQLite needs init** - the SQLite layer skips until Warp has launched once and created `warp.sqlite`. A fresh host shows SKIP, not FAIL.
- **Windows symlinks** - need Developer Mode or elevation for the launch-config walk, same caveat as the skills sweep.

## See also

- [warp-host-setup.md](warp-host-setup.md) - channel split, install playbook, URI scheme, subdir reference.
- [tooling-warp skill](../.agents/skills/tooling-warp/SKILL.md) - agent-facing usage.
- [README.md](../README.md) - repo intro.

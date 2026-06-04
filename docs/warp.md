# Warp config module

The `warp/` Go module establishes and verifies Kai's Warp terminal config across hosts. Run it through coily, never bare `go`:

- `coily exec warp apply` - host-aware, idempotent: reconcile every state layer.
- `coily exec warp doctor` - verify only: PASS/FAIL per check, no mutation.

The repo is the source of truth. `apply` pushes the repo's intent onto the host, `doctor` reports drift without touching anything. Both resolve the repo root by walking up from cwd to the first `.git`, so they work from any subdir and adapt automatically when the checkout moves.

## State layers

`apply` reconciles four kinds of state, each with a matching `doctor` check:

- **Rendered files** - `settings.toml`, the theme YAML, `tab_configs/startup_config.toml`. Embedded templates rendered to real files (not symlinks) in the Warp config dir. Drift = content mismatch.
- **Launch-config symlinks** - every `warp/launch_configurations/*.yaml` is symlinked into the config dir's `launch_configurations/`, and dangling links are swept. See [launch configs](#launch-configs) below.
- **SQLite settings** - keys in Warp's `warp.sqlite` that have no TOML surface (see `mapping.go`). Skipped until Warp has initialized the DB once.
- **Wallpaper** - existence check only.

## Per-OS config dir

`paths.go` resolves the layout per OS. The config dir is:

- **macOS** - `~/.warp/`. SQLite lives under the Preview bundle (`dev.warp.Warp-Preview`), since Kai's Mac daily driver is Warp Preview.
- **Windows** - `%LOCALAPPDATA%\warp\Warp\config\`. Themes scan `%APPDATA%` (Roaming), a separate path.
- **Linux** - `~/.config/warp-terminal/`.

`WorkspaceDir` is the parent of the repo root. `StartupDir` (where a fresh tab opens) is one level above that on Mac/Linux, flat on Windows.

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

# Warp config module

The `warp/` Go module establishes and verifies Kai's Warp terminal config across hosts. Run it through ward, never bare `go`:

- `just warp apply` - host-aware, idempotent: reconcile every state layer.
- `just warp doctor` - verify only: PASS/FAIL per check, no mutation.

The repo is the source of truth. `apply` pushes the repo's intent onto the host, `doctor` reports drift without touching anything. Both resolve the repo root by walking up from cwd to the first `.git`, so they work from any subdir.

## State layers

`apply` reconciles four kinds of state, each with a matching `doctor` check:

- **Rendered files** - `settings.toml`, `keybindings.yaml`, the theme YAML, `tab_configs/startup_config.toml`. Embedded templates rendered to real files (not symlinks) in the Warp config dir. Drift = content mismatch, except [volatile keys](warp.md) doctor skips.
- **Launch-config symlinks** - every `warp/launch_configurations/*.yaml` is symlinked into the config dir's `launch_configurations/`, and dangling links are swept. See [launch configs](#launch-configs) below.
- **SQLite settings** - keys in Warp's `warp.sqlite` with no TOML surface (see `mapping.go`), plus a Windows-only [default-shell pref](warp.md). Skipped until Warp inits the DB.
- **Wallpaper** - existence check only.

## Per-OS config dir

`paths.go` resolves the layout per OS. The config dir is:

- **macOS** - channel-aware. Preview (default) at `~/.warp-preview/` with SQLite under `dev.warp.Warp-Preview`, Stable (fallback) at `~/.warp/` with SQLite under `dev.warp.Warp-Stable`.
- **Windows** - channel-aware: `%LOCALAPPDATA%\warp\WarpPreview\` or `...\warp\Warp\`, config in `<channel>\config\`, SQLite in `<channel>\data\`. Themes scan `%APPDATA%` (Roaming).
- **Linux** - `~/.config/warp-terminal/`.

On macOS and Windows the two channels coexist, so `apply`/`doctor` pick one and target its config dir and SQLite together. Selection: `--channel preview|stable` (or `WARP_CHANNEL` env) wins, else auto-detect by installed app (macOS `/Applications`, Windows `%LOCALAPPDATA%\Programs`), **preferring Preview**. The resolved channel is echoed in the header line. Linux is single-channel and ignores the flag.

`WorkspaceDir` is the parent of the repo root. `StartupDir` (where a fresh tab opens) is one level above that on every OS.

## Launch configs

Launch configs are mirrored, not rendered: the repo dir is the source, the config dir holds a symlink per `*.yaml`. `apply` creates any missing link, repoints a stale one, and sweeps links that no longer resolve. It is idempotent - a link already pointing at the right source is left alone - and it never touches real files or healthy unrelated links. A pre-existing real file at a target is backed up to `<name>.bak` before linking.

The walk exists because hand-made links went orphaned: a new or moved launch config stayed invisible to Warp until someone ran `ln -s` by hand. Implementation in `launch.go`.

`tab_configs/` entries beyond the rendered `startup_config.toml` remain hand-placed real files, not part of this walk.

## Sharp edges

- **Preview vs Stable** - two channels coexist with separate config dirs and URL schemes. `warppreview://` always lands in Preview, `warp://` in Stable.
- **Stuck mouse-tracking flood** - a child that dirties DECSET 1003 floods the pane. `ctrl-shift-m` clears it mid-director, no TUI kill. See [warp-host-setup.md](warp-host-setup.md).
- **SQLite needs init** - the SQLite layer skips until Warp has launched once and created `warp.sqlite`. A fresh host shows SKIP, not FAIL.
- **Windows symlinks** - need Developer Mode or elevation for the launch-config walk, same caveat as the skills sweep.

## Warp-owned volatile settings

`just warp apply` renders `settings.toml` from `warp/templates/settings.toml.tmpl` and `just warp doctor` checks the on-disk file against that same render. The default check is byte-for-byte: any difference is drift and FAILs.

A few keys break that model. The running Warp persists live UI and cloud-account state back into `settings.toml` on every launch, overwriting whatever `apply` wrote. Pinning them in the template guarantees perpetual doctor drift no matter what value the template carries.

## The volatile keys

The allowlist is `volatileSettingsKeys` in `warp/main.go`:

- `zoom_level` (under `[appearance.window]`) - Warp writes the live window zoom. The template pins a value, but Warp rewrites it to whatever the window is currently at.
- `cloud_conversation_storage_enabled` (under `[agents]`) - Warp mirrors cloud account state here on every launch, regardless of `is_settings_sync_enabled`. The only way to actually pin it false is the Warp UI toggle, which then makes Warp write `false` itself.

## How doctor handles them

For each volatile key, doctor neutralizes the key's **value** (not the line) in both the canonical render and the on-disk file before comparing, via `reconcileVolatile` / `neutralizeKey` in `warp/main.go`. A value-only difference therefore no longer counts as drift, and doctor emits a `NOTE` showing `template=<x> live=<y>` instead of a `FAIL`.

Only the scalar value is exempt. The key line itself must still be present and in place, so the template keeps emitting both keys (and `cloud_conversation_storage_enabled` keeps its documenting comment). Structural drift - a missing key line, a moved section header, a renamed key - still FAILs. The neutralization is also prefix-safe: `zoom_level` never matches a longer key like `max_zoom_level`.

## Adding a key

Add the TOML key name to `volatileSettingsKeys` in `warp/main.go`. Only do this for keys Warp genuinely owns and rewrites from live state - everything else should stay an enforced byte-for-byte match. See this page for the original motivation.

## Warp default-shell layer

On Windows, "which shell Warp launches for new tabs" (Settings > Features > Session, choosing among PowerShell / Git Bash / WSL / Cmd) is stored only in `warp.sqlite`. It has no `settings.toml` surface, so before this layer it drifted across machines and stayed invisible to `warp doctor`. The `warp/` module now manages it alongside the other SQLite keys (see [warp.md](warp.md)).

## Behaviour

- **apply** - resolves PowerShell 7 from disk and writes its path under the default-shell key in `warp.sqlite`. Idempotent: a converged value is left alone. Skips with a clear line when no PowerShell 7 is installed.
- **doctor** - reports drift when the live value differs from the resolved shell, fails when the key is absent, and NOTE-skips when PowerShell 7 is not installed.
- **macOS / Linux** - use the login shell and have no managed pref, so the layer is Windows-only and silently inert there.

## Public-safe path resolution

The desired shell is the path to the first PowerShell 7 binary found among the standard machine-class install locations (`C:\Program Files\PowerShell\7\pwsh.exe` and the `7-preview` sibling). Those segments carry no user-specific identity, so resolving at runtime - rather than hardcoding a machine-specific path into the repo - keeps the layer public-safe. The same candidate list backs `resolvePwshProfile` in `render.go`. Implementation lives in `warp/shell.go`; `HostPaths.DefaultShell` carries the resolved value.

## The inferred storage key

Warp does not document the `generic_string_objects` `storage_key` for this preference, and it can only be confirmed against a live Windows `warp.sqlite`. The key is set from a single constant (`defaultShellStorageKey`) in `warp/shell.go`. A wrong key is harmless - Warp ignores unknown rows - but it makes the layer a silent no-op rather than truly converging the UI setting. If a host ever shows the shell drifting in the Warp UI despite a green `apply`, dump the DB's `generic_string_objects` keys and reconcile the constant (and the value shape, if Warp stores more than a bare path).

See this page for the original request.

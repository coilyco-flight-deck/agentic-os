# Warp host setup

Per-host install and channel layout for Warp. The module model (apply/doctor, state layers, paths) lives in [warp.md](warp.md).

## Channels

Two Warp channels coexist on the Mac daily driver with separate bundle ids, URL schemes, and config dirs. Preview is the default-clicked terminal, Stable the named fallback.

- **Preview** (daily driver) - `/Applications/WarpPreview.app`, bundle `dev.warp.Warp-Preview`, scheme `warppreview://`, config dir `~/.warp-preview/`. Install: `coily pkg brew install --cask warp@preview --allow-untapped`.
- **Stable** (fallback) - `/Applications/Warp.app`, bundle `dev.warp.Warp-Stable`, scheme `warp://`, config dir `~/.warp/`. Install: `coily pkg brew install --cask warp --allow-untapped`.

URL schemes are channel-specific by design: `warp://` always lands in Stable, `warppreview://` in Preview. There is no LaunchServices "default Warp" toggle that flips this, so tooling picks the channel by scheme at the call site.

Preview auto-symlinks `launch_configurations`, `tab_configs`, and `themes` into `~/.warp/` on first launch, so checked-in configs cover both channels for free. `settings.toml` is the one file that does not auto-share - the dual-channel install points Preview's `settings.toml` at the same source as Stable's.

## Install playbook (Mac daily driver)

1. `coily pkg brew install --cask warp@preview --allow-untapped` installs `/Applications/WarpPreview.app`.
2. Launch Preview once. It creates `~/.warp-preview/` and auto-symlinks the shared subdirs.
3. Point Preview's `settings.toml` at this repo's copy:
   ```sh
   rm ~/.warp-preview/settings.toml
   ln -s /Users/kai/projects/coilyco-flight-deck/agentic-os/warp/settings.toml ~/.warp-preview/settings.toml
   ```
4. Run `scripts/set-warp-default-editor.sh` to bind file-type defaults to Preview (markdown, python, go, the js/ts family, json, plain text, generic source UTI). It honors `WARP_DEFAULT_EDITOR_BUNDLE_ID` and `WARP_DEFAULT_EDITOR_APP_PATH` for per-host overrides.
5. Pin WarpPreview in the Dock, unpin Warp. Reach for it via Spotlight by typing `warppreview`.

Then `coily exec warp apply` reconciles the rest (settings, theme, launch configs, SQLite).

## Fallback to Stable

When a Preview regression breaks a workday:

- `open -a Warp` opens Stable by bundle name.
- `warp://` URIs always route to Stable - useful for known-good URI tests.
- `coily pkg brew upgrade --cask warp@preview --allow-untapped` picks up the next Preview release. Warp ships weekly.

## Subdirs

- `launch_configurations/` - one window, one-or-more tabs per YAML. URI `warppreview://launch/<name>`. `apply` symlinks each into the config dir and sweeps dangling links.
- `tab_configs/` - one tab per TOML, opens in the active window. URI `warppreview://tab_config/<name>`. Handler landed in warpdotdev/Warp#9379 (Warp builds dated 2026-05-15 or later).
- `themes/` - color theme YAML files.
- `scripts/` - host-side helpers (`set-warp-default-editor.sh`).
- `settings.toml` - top-level settings, symlinked into both channels' config dirs.

## See also

- [warp.md](warp.md) - the Go module's model (apply/doctor, layers, paths).
- [tooling-warp skill](../.agents/skills/tooling-warp/SKILL.md) - agent-facing usage.
- coilysiren/coily#270 - `coily dispatch interactive`, which fires `warp://launch/...`.
- warpdotdev/Warp#9379 - the merged tab_config URI handler that motivated the Preview move.

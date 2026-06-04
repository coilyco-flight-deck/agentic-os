# Warp config

Checked-in Warp configuration sources. Loaded by Warp when symlinked into the per-channel config dir under `$HOME`.

## Channel split

Two Warp channels are installed on the Mac daily driver: **Preview** is the default-clicked terminal, **Stable** is the named fallback for when Preview wedges. Both apps coexist with separate bundle identifiers and separate URL schemes.

| Surface | Stable | Preview |
| --- | --- | --- |
| App bundle | `/Applications/Warp.app` | `/Applications/WarpPreview.app` |
| Bundle id | `dev.warp.Warp-Stable` | `dev.warp.Warp-Preview` |
| URL scheme | `warp://` | `warppreview://` |
| Config dir | `~/.warp/` | `~/.warp-preview/` |
| Install | `coily pkg brew install --cask warp --allow-untapped` | `coily pkg brew install --cask warp@preview --allow-untapped` |

URL schemes are channel-specific by design. `warp://` always lands in Stable. `warppreview://` always lands in Preview. There is no macOS LaunchServices "default Warp" setting that flips this. Tooling that fires Warp URIs picks the channel by scheme at call site.

Preview's config dir auto-symlinks `launch_configurations`, `tab_configs`, and `themes` into `~/.warp/` on first launch, so checked-in configs from this repo cover both channels for free. `settings.toml` is the one file that does not auto-share. The dual-channel install symlinks Preview's `settings.toml` to the same source as Stable's so they stay in sync.

## Install playbook for the Mac daily driver

1. `coily pkg brew install --cask warp@preview --allow-untapped` installs `/Applications/WarpPreview.app`.
2. Launch Preview once. It creates `~/.warp-preview/` and auto-symlinks the shared subdirs.
3. Replace Preview's fresh `~/.warp-preview/settings.toml` with a symlink to this repo's `settings.toml`:
   ```sh
   rm ~/.warp-preview/settings.toml
   ln -s /Users/kai/projects/coilyco-flight-deck/agentic-os/warp/settings.toml ~/.warp-preview/settings.toml
   ```
4. Bind file-type defaults to Preview by running [`scripts/set-warp-default-editor.sh`](scripts/set-warp-default-editor.sh). Covers markdown, python, go, the javascript/typescript family, json, plain text, and the generic source-code UTI. The script reads `WARP_DEFAULT_EDITOR_BUNDLE_ID` and `WARP_DEFAULT_EDITOR_APP_PATH` env vars so you can override per-host (e.g. to pin a non-Mac fallback to Stable).
5. Manual: pin WarpPreview in the Dock, unpin Warp. Use Spotlight by typing `warppreview` rather than `warp` when reaching for the daily driver.

## Fallback to Stable

When a Preview regression breaks a workday:

- `open -a Warp` opens Stable explicitly by bundle name.
- `warp://` URIs always route to Stable. Useful for known-good URI tests.
- `coily pkg brew upgrade --cask warp@preview --allow-untapped` picks up the next Preview release. Warp ships weekly.

## Subdirs

- [`launch_configurations/`](launch_configurations/README.md) - one window with one or more tabs per YAML file. Window-scoped, opens a fresh window each fire. URI: `warp://launch/<name>` or `warppreview://launch/<name>`. `coily exec warp apply` symlinks every `*.yaml` here into the Warp config dir's `launch_configurations/` and sweeps dangling links, so a new entry (or a moved checkout) reaches Warp without a hand `ln -s`.
- [`tab_configs/`](tab_configs/) - one tab per TOML file, opens in the active window. URI: `warp://tab_config/<name>` or `warppreview://tab_config/<name>`. The URI handler landed in warpdotdev/Warp#9379 (merged 2026-05-15) and is available in any Warp build dated 2026-05-15 or later, both channels. Current entries: `startup_config.toml` (the "+ button" new-tab default) and `claude-dispatch-interactive.toml` (companion to the `launch_configurations/` entry of the same name, used when `coily dispatch interactive` fires with `--surface tab`, which is the default).
- [`themes/`](themes/) - color theme YAML files.
- [`scripts/`](scripts/) - host-side helpers (e.g. `set-warp-default-editor.sh`).
- `settings.toml` - top-level Warp settings, symlinked into both channels' config dirs.

## See also

- #10 - automate the `warp/launch_configurations/*.yaml` symlink walk into the Warp config dir. Done: `apply` now walks and sweeps (see `launch.go`). The same plumbing gap still applies to `tab_configs/` (those remain hand-placed real files).
- coilysiren/agentic-os#107 - the dual-channel install that produced this doc.
- coilysiren/coily#270 - `coily dispatch interactive` which consumes Warp URIs. Currently fires `warp://launch/...`; channel-aware variants are a follow-up.
- warpdotdev/Warp#9379 - merged tab_config URI handler that motivated moving to Preview as the daily driver.

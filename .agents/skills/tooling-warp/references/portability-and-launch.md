# Warp host portability, launch configs, and common edits

## Host and channel portability

One line is host-absolute and points at the Stable config dir specifically:

- `[general] default_tab_config_path = "/Users/kai/.warp/tab_configs/startup_config.toml"`

This resolves correctly under Preview only because `~/.warp-preview/tab_configs` auto-symlinks to `~/.warp/tab_configs`. If Stable is ever uninstalled, the symlink target disappears and Preview loses its startup tab. Same shape on Windows, where the path becomes `C:\Users\kai\.warp\tab_configs\startup_config.toml`.

Options when this bites:

1. Per-host override - leave the canonical path in the repo, hand-edit the Windows copy after symlinking (breaks symlink-as-source-of-truth).
2. Drop `default_tab_config_path` entirely - Warp falls back to a default new-tab. Re-add only if the named startup tab is needed.
3. Anchor through a path both channels resolve independently (no symlink chain). Open.

Until Kai installs on Windows or removes Stable, leave the Mac/Stable-shaped path as-is.

## Launch configurations and tab configs

Two URI-addressable spawn primitives, checked into `agentic-os/warp/`:

- **`launch_configurations/*.yaml`** - one window with one or more tabs per file. Window-scoped, opens a fresh window each fire. URI: `warp://launch/<name>` or `warppreview://launch/<name>`.
- **`tab_configs/*.toml`** - one tab per file, opens in the active window. URI: `warp://tab_config/<name>` or `warppreview://tab_config/<name>`. The tab_config URI handler landed in warpdotdev/Warp#9379, shipped to Preview 2026-05-13+ and Stable 2026-05-15+. This is the load-bearing capability that motivated promoting Preview to the daily driver, since `ward agent <mode> work <ref> --new-tab` (ward#174, formerly `ward dispatch interactive`, ward#270) consumes the URI.

URI scheme picks the channel. `warp://` always opens Stable, `warppreview://` always opens Preview. Tooling that fires Warp URIs picks at call site.

Symlink walk: `agentic-os/warp/{launch_configurations,tab_configs}/*` need to land in `~/.warp/{launch_configurations,tab_configs}/` (Preview's auto-symlink picks them up from there). Currently manual per-file - see coilysiren/agentic-os#106 for the automation gap.

## Common edits

- **Theme** - `[appearance.themes] theme = "phenomenon"`. Other built-ins live under Warp's Settings > Appearance.
- **Font size** - `[appearance.text] font_size = 11.0` and `notebook_font_size = 14.0`.
- **Custom secret regexes** - `[privacy] custom_secret_regex_list` is a TOML array of `{ name, pattern }` tables. Patterns are detection-only (block redaction is off, see `[privacy.secret_redaction] enabled = false`).
- **Subshell auto-warpify** - `[warpify.subshells] added_subshell_commands` makes Warp render blocks for commands like `docker compose run` that drop into an inner shell.

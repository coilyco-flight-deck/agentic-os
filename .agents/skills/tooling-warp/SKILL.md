---
name: tooling-warp
description: Warp is Kai's terminal on every host. Block-mode shell with left-side vertical tabs, one shell per tab. Preview is the Mac daily driver, Stable is the fallback.
---

# Warp

The terminal on every host. Block-mode UI with left-side vertical tabs.

## Use when

Editing Warp config, debugging UI noise, adjusting tab behavior, configuring shells per-OS, tuning Warp AI/agent surfaces, or wiring `launch_configurations` / `tab_configs` URI handlers.

## Triggers

warp, Warp, WarpPreview, ~/.warp, ~/.warp-preview, warp settings, settings.toml, vertical tabs, warp tabs, launch configuration, tab config, warp blocks, warp ai, warp agent, warpify, subshell, startup_config, warp://, warppreview://.

## Channels

Two Warp channels on the Mac daily driver. **Preview is the default-clicked terminal**, Stable is the fallback for when Preview wedges. Both coexist with separate bundle ids and URL schemes.

| Surface | Stable | Preview |
| --- | --- | --- |
| App | `/Applications/Warp.app` | `/Applications/WarpPreview.app` |
| Bundle id | `dev.warp.Warp-Stable` | `dev.warp.Warp-Preview` |
| URL scheme | `warp://` | `warppreview://` |
| Config dir | `~/.warp/` | `~/.warp-preview/` |
| Spotlight | `warp` | `warppreview` |
| Brew | `warp` | `warp@preview` |

URL schemes are channel-specific. `warp://` always lands in Stable, `warppreview://` always lands in Preview. There is no macOS LaunchServices "default Warp" toggle that flips this. Tooling that fires Warp URIs picks the channel by scheme at call site.

Preview was made the daily driver after warpdotdev/Warp#9379 (the `tab_config` URI handler) landed - that handler shipped to Preview builds dated 2026-05-13 or later, Stable builds 2026-05-15 or later. See `warp/README.md` for the install playbook (brew install, manual `settings.toml` symlink swap, `scripts/set-warp-default-editor.sh` to rebind file-type defaults via `duti` + `lsregister`).

## Config location

Canonical files live at `~/projects/coilysiren/agentic-os/warp/`, symlinked into both channels' config dirs:

- `~/.warp/settings.toml` -> `agentic-os/warp/settings.toml`
- `~/.warp/tab_configs/startup_config.toml` -> `agentic-os/warp/tab_configs/startup_config.toml`
- `~/.warp-preview/settings.toml` -> `agentic-os/warp/settings.toml` (same file, hand-symlinked per the README playbook because Warp doesn't auto-share `settings.toml` across channels)
- `~/.warp-preview/{launch_configurations,tab_configs,themes}` -> `~/.warp/...` (auto-symlinked by Preview on first launch)

The net effect: one source of truth in the repo, both channels read it.

## Cloud-sync gotcha

`[account] is_settings_sync_enabled` is forced to `false` in the committed copy. If Warp's cloud settings-sync is on, it overwrites the symlink target on every settings-touch from any device, fighting the repo. The repo wins; cross-device sync is given up on purpose.

If a settings-pane toggle silently disappears the next time Warp restarts, suspect cloud-sync was flipped back on and check `[account]` in the file.

## Why Warp instead of a classic terminal

Two pieces, together. Don't regress either:

- **Block-mode terminal.** Each command groups with its output as a discrete block. Click any past block to copy, share, or jump back. Errors get a red gutter. Long output collapses. This is the main reason Warp exists.
- **Tab as session anchor.** Each vertical tab keeps its own cwd, scrollback, env, and running processes. Switching tabs is switching context, not re-typing it. Like browser tabs for shell sessions.

The unit of work is a block, the unit of context is a tab.

## Tab discipline

Kai's typical Warp session is 4-7 tabs, one shell per tab, no splitting:

- 1 plain shell (true blank canvas).
- 1 file viewer (running `bat`-wrapped reflexes, see coilysiren/agentic-os#57).
- 1 status watcher (running `watch -n 5 '<command>'` for health checks).
- 4 cloud agents (typically Claude Code sessions).
- Optional: 1 persistent `ssh kai-server` tab if homelab work is hot.

Panes are off. Splitting one tab into multiple panes is rejected as a navigation primitive; if a status display is needed, it gets its own tab. This is why `display_granularity = "tabs"` (not `"panes"`).

## Settings that must not regress

In `[appearance.vertical_tabs]`:

- `enabled = true` - vertical tabs on. The whole UX bet.
- `primary_info` - per docs, valid values are `{command, working_directory, branch}`. Kai rejected `working_directory` because she's in `~/projects/coilysiren/*` 95% of the time. Current value is settled in the UI; whatever it is, don't revert to `working_directory`.
- `compact_subtitle` - per docs, valid values are `{branch, working_directory}`, but `command` is also accepted (undocumented variant). Current value lives in the file and is settled.
- `display_granularity = "tabs"` - one row per tab, not per pane. Panes are off, see tab discipline above.

`primary_info = "process"` is NOT a valid value, even though it sounds plausible. Setting it logs `Failed to parse file value for setting VerticalTabsPrimaryInfo` then `Inhibiting writes for setting key appearance.vertical_tabs.primary_info` in `~/Library/Logs/warp.log`, after which the file's value for that key is ignored.

## Host and channel portability

One line is host-absolute and points at the Stable config dir specifically:

- `[general] default_tab_config_path = "/Users/kai/.warp/tab_configs/startup_config.toml"`

This resolves correctly under Preview only because `~/.warp-preview/tab_configs` auto-symlinks to `~/.warp/tab_configs`. If Stable is ever uninstalled, the symlink target disappears and Preview loses its startup tab. Same shape on Windows, where the path becomes `C:\Users\kai\.warp\tab_configs\startup_config.toml`.

Options when this bites:

1. Per-host override - leave the canonical path in the repo, hand-edit the Windows copy after symlinking (breaks symlink-as-source-of-truth).
2. Drop `default_tab_config_path` entirely - Warp falls back to a default new-tab. Re-add only if the named startup tab is needed.
3. Anchor through a path both channels resolve independently (no symlink chain). Open.

Until Kai installs on Windows or removes Stable, leave the Mac/Stable-shaped path as-is.

## Deep internals

AI/agent noise-cut, the `settings.toml` <-> SQLite model, schema-enum debugging, and inline rich rendering live in [`references/internals.md`](references/internals.md).

## Launch configurations and tab configs

Two URI-addressable spawn primitives, checked into `agentic-os/warp/`:

- **`launch_configurations/*.yaml`** - one window with one or more tabs per file. Window-scoped, opens a fresh window each fire. URI: `warp://launch/<name>` or `warppreview://launch/<name>`.
- **`tab_configs/*.toml`** - one tab per file, opens in the active window. URI: `warp://tab_config/<name>` or `warppreview://tab_config/<name>`. The tab_config URI handler landed in warpdotdev/Warp#9379, shipped to Preview 2026-05-13+ and Stable 2026-05-15+. This is the load-bearing capability that motivated promoting Preview to the daily driver, since `coily dispatch interactive` (coilysiren/coily#270) consumes the URI.

URI scheme picks the channel. `warp://` always opens Stable, `warppreview://` always opens Preview. Tooling that fires Warp URIs picks at call site.

Symlink walk: `agentic-os/warp/{launch_configurations,tab_configs}/*` need to land in `~/.warp/{launch_configurations,tab_configs}/` (Preview's auto-symlink picks them up from there). Currently manual per-file - see coilysiren/agentic-os#106 for the automation gap.

## Common edits

- **Theme** - `[appearance.themes] theme = "phenomenon"`. Other built-ins live under Warp's Settings > Appearance.
- **Font size** - `[appearance.text] font_size = 11.0` and `notebook_font_size = 14.0`.
- **Custom secret regexes** - `[privacy] custom_secret_regex_list` is a TOML array of `{ name, pattern }` tables. Patterns are detection-only (block redaction is off, see `[privacy.secret_redaction] enabled = false`).
- **Subshell auto-warpify** - `[warpify.subshells] added_subshell_commands` makes Warp render blocks for commands like `docker compose run` that drop into an inner shell.

## See also

- [`warp/README.md`](../../../warp/README.md) - install playbook for the Mac daily driver (brew install Preview, swap `settings.toml` symlink, run `scripts/set-warp-default-editor.sh` to rebind file-type defaults via `duti` + `lsregister`, Dock/Spotlight discipline). The script honors `WARP_DEFAULT_EDITOR_BUNDLE_ID` and `WARP_DEFAULT_EDITOR_APP_PATH` for per-host overrides.
- coilysiren/agentic-os#106 - automate the `warp/launch_configurations/*` and `warp/tab_configs/*` symlink walk into `~/.warp/`.
- coilysiren/agentic-os#107 - dual-channel install (the Preview promotion).
- coilysiren/coily#270 - `coily dispatch interactive`, the consumer of the Warp tab_config URI handler.
- warpdotdev/Warp#9379 - merged tab_config URI handler that motivated moving to Preview as the daily driver.
- coilysiren/agentic-os#57 - terminal file-viewer wrapper functions (`bat`, `view`, `open`, etc.).
- coilysiren/agentic-os#58 - Brewfile catalog of modern CLI tools.

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

## AI / Agent surface (the noise-cut)

Kai uses Claude Code for AI work; Warp is terminal-only. The master kill switch is:

- `[agents.warp_agent] is_any_ai_enabled = false`

Set this, the entire Warp Agent surface goes dark. Every sub-toggle (Active AI, Next Command, Prompt Suggestions, Autodetect agent prompts, Autodetect terminal commands, etc.) is gated by it.

The sub-knobs (under `[agents.warp_agent.input]`, `[agents.profiles]`, `[agents.knowledge]`, `[agents.warp_agent.active_ai]`, `[code.indexing]`) are kept set to `false` in the file as defense in depth. They don't have effect while the master is off, but they stop noise from leaking back if anything ever flips the master.

The third-party CLI-agent surface is separate from the Warp Agent. `[agents.third_party] auto_open_composer_on_cli_agent_start` controls whether Warp opens its composer panel when a CLI agent like Claude Code starts. With `is_any_ai_enabled = false`, the composer is also dead weight - keep `auto_open_composer_on_cli_agent_start = false`.

Two AI-adjacent visual chips that sneak past the master switch:

- `[appearance.tabs.header_toolbar_chip_selection.custom] left = [..., "code_review"]` - Warp's AI-driven code review chip in the toolbar.
- `[code.editor] show_code_review_button = true` - the in-block button for the same surface.

Both are vestigial with AI off. Drop `code_review` from the chip list and set `show_code_review_button = false`.

The one knob that resists file edits is `[agents] cloud_conversation_storage_enabled`. Warp rewrites `true` to it on every cold launch from cloud account state, regardless of `is_settings_sync_enabled = false`. To actually disable, toggle the corresponding option in Warp's UI. After that Warp will write `false` to both the file and its account state.

`[general] default_session_mode = "terminal"` is separate from the AI surface but related: it controls whether a new tab opens as a shell or as a chat surface. Keep at `"terminal"`.

Cmd+I (open Warp Agent panel): no documented file-level disable. Empirically the master kill switch is enough - the panel opens but is inert. If a hard rebind is needed, Warp's keybindings live in Settings > Keybindings.

## How settings.toml interacts with SQLite

Per Warp's docs, the app watches `settings.toml` and applies changes instantly. Empirically observed behavior matches:

- The file is the source of truth at startup. Warp reads it, applies values to in-memory state.
- When you change something in the Warp UI, Warp writes the new value back to `settings.toml`. Existing keys get updated in place. New sections get appended.
- A parallel SQLite store (`~/Library/Group Containers/2BBY89MBSN.dev.warp/Library/Application Support/dev.warp.Warp-Stable/warp.sqlite`, table `generic_string_objects`, keyed by `storage_key`) caches the same state. Both file and SQLite end up holding the same values after a UI change.
- The one observed exception is `cloud_conversation_storage_enabled`, which Warp rewrites from cloud account state on every cold launch regardless of `is_settings_sync_enabled = false`. Cloud account state is its own source of truth for that key.

For peeking at SQLite to debug a setting mystery, each channel has its own DB. Pick the channel running the misbehaving Warp:

```bash
# Preview (daily driver)
sqlite3 ~/Library/Group\ Containers/2BBY89MBSN.dev.warp/Library/Application\ Support/dev.warp.Warp-Preview/warp.sqlite \
  "SELECT data FROM generic_string_objects ORDER BY id;" | grep -i <KeyNamePartial>

# Stable (fallback)
sqlite3 ~/Library/Group\ Containers/2BBY89MBSN.dev.warp/Library/Application\ Support/dev.warp.Warp-Stable/warp.sqlite \
  "SELECT data FROM generic_string_objects ORDER BY id;" | grep -i <KeyNamePartial>
```

The `storage_key` is the SQLite name (e.g. `VerticalTabsPrimaryInfo`); the TOML path is the snake_case form under the corresponding section (e.g. `[appearance.vertical_tabs] primary_info`). Map between the two by grepping the Warp binary - the inner binary name differs per channel:

```bash
# Preview - binary is named `preview`
strings /Applications/WarpPreview.app/Contents/MacOS/preview | grep -oE '[a-z_]+\.[a-z_]+\.[a-z_]+'

# Stable - binary is named `stable`
strings /Applications/Warp.app/Contents/MacOS/stable | grep -oE '[a-z_]+\.[a-z_]+\.[a-z_]+'
```

## settings.toml schema gotchas

Enums in this file are strict-validated against Rust enum variants in the Warp binary. Wrong values get a `Failed to parse file value for setting <Name>` error in `~/Library/Logs/warp.log` and an `Inhibiting writes for setting key <key>` follow-up, after which Warp ignores the file's value entirely. Recovery is to fix the value and relaunch.

Three places to find valid values, in order of trust:

1. **The docs** - [all-settings reference](https://docs.warp.dev/terminal/settings/all-settings/) and [settings file overview](https://docs.warp.dev/terminal/settings/). Authoritative for what's officially supported.
2. **The Warp binary** - grep for enum variants directly:

   ```bash
   strings /Applications/WarpPreview.app/Contents/MacOS/preview | grep -oE '<EnumName>[A-Z][a-zA-Z]*' | sort -u
   ```

   (Stable binary path is `/Applications/Warp.app/Contents/MacOS/stable`; same grep, same enum set in practice.)

   For example, `VerticalTabsPrimaryInfo` resolves to `{Command, WorkingDirectory, Branch}` (serialized as snake_case in TOML: `command`, `working_directory`, `branch`).
3. **Set it in the UI and read what Warp writes to the file.** Most reliable but slow.

Note: some accepted values are undocumented (e.g. `compact_subtitle = "command"` is accepted by Warp but not in the docs). Trust the binary over the docs when they disagree.

## Inline rich rendering

Warp renders:

- Clickable URLs and clickable file paths in output (OSC 8 hyperlinks).
- Images via the iTerm2 inline image protocol. So `imgcat foo.png` shows the image in the block.
- Pretty-printed tables when output is structured (e.g. `ls -l`).

The `open` wrapper in coilysiren/agentic-os#57 routes image extensions to `imgcat` and falls back to `command open` for everything else. `chafa` is the universal terminal image/video renderer if Warp's native protocol doesn't cover a case.

Less sure: whether Warp renders raw markdown in shell-mode output (agent panel definitely does). Verify when relevant.

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

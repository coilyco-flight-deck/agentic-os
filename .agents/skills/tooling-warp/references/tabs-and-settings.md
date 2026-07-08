# Warp tab discipline and non-regressing settings

## Why Warp instead of a classic terminal

Two pieces, together. Don't regress either:

- **Block-mode terminal.** Each command groups with its output as a discrete block. Click any past block to copy, share, or jump back. Errors get a red gutter. Long output collapses. This is the main reason Warp exists.
- **Tab as session anchor.** Each vertical tab keeps its own cwd, scrollback, env, and running processes. Switching tabs is switching context, not re-typing it. Like browser tabs for shell sessions.

The unit of work is a block, the unit of context is a tab.

## Tab discipline

Kai's typical Warp session is 4-7 tabs, one shell per tab, no splitting:

- 1 plain shell (true blank canvas).
- 1 file viewer (running `bat`-wrapped reflexes, see the file-viewer wrappers).
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

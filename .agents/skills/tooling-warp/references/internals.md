# Warp deep internals

Forensic / deep-config reference for `tooling-warp`. The operational core stays in SKILL.md; this file holds the AI-surface noise-cut, the `settings.toml` <-> SQLite model, schema-enum debugging, and inline rendering.

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

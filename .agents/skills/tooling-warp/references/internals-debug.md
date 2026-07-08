# Warp internals: SQLite peeking, schema gotchas, rendering

Companion to [`internals.md`](internals.md). Covers debugging the `settings.toml` <-> SQLite mapping, enum schema validation, and inline rich rendering.

## Peeking at SQLite to debug a setting

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

The `open` wrapper routes image extensions to `imgcat` and falls back to `command open` for everything else. `chafa` is the universal terminal image/video renderer if Warp's native protocol doesn't cover a case.

Less sure: whether Warp renders raw markdown in shell-mode output (agent panel definitely does). Verify when relevant.

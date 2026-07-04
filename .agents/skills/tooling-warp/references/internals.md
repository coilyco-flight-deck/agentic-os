# Warp deep internals

Forensic / deep-config reference for `tooling-warp`. The operational core stays in SKILL.md; this file holds the AI-surface noise-cut and the `settings.toml` <-> SQLite model. SQLite peeking, enum-source trust order, schema gotchas, and inline rendering live in [`internals-debug.md`](internals-debug.md).

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

Cmd+I (open Warp Agent panel): no documented file-level disable. Empirically the master kill switch is enough - the panel opens but is inert. If a hard rebind is needed, Warp's keybindings live in Settings > Keybindings, or in the rendered `keybindings.yaml`.

`apply` renders `keybindings.yaml` (a layer-2 file, sibling of `settings.toml`) with one managed binding, `"workspace:toggle_mouse_reporting": "ctrl-shift-m"` - a mid-director escape hatch that clears a stuck xterm mouse-tracking (1003) flood at the Warp emulator layer without killing the TUI. See [warp-mouse-tracking.md](../../../../docs/warp-mouse-tracking.md) and #320.

## How settings.toml interacts with SQLite

Per Warp's docs, the app watches `settings.toml` and applies changes instantly. Empirically observed behavior matches:

- The file is the source of truth at startup. Warp reads it, applies values to in-memory state.
- When you change something in the Warp UI, Warp writes the new value back to `settings.toml`. Existing keys get updated in place. New sections get appended.
- A parallel SQLite store (`~/Library/Group Containers/2BBY89MBSN.dev.warp/Library/Application Support/dev.warp.Warp-Stable/warp.sqlite`, table `generic_string_objects`, keyed by `storage_key`) caches the same state. Both file and SQLite end up holding the same values after a UI change.
- The one observed exception is `cloud_conversation_storage_enabled`, which Warp rewrites from cloud account state on every cold launch regardless of `is_settings_sync_enabled = false`. Cloud account state is its own source of truth for that key.

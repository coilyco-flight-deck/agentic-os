# Warp config location and cloud-sync gotcha

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

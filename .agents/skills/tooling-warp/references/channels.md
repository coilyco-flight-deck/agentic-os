# Warp channels (Stable vs Preview)

Two Warp channels on the Mac daily driver. **Preview is the default-clicked terminal**, Stable is the fallback for when Preview wedges. Both coexist with separate bundle ids and URL schemes.

- **App** - Stable `/Applications/Warp.app` - Preview `/Applications/WarpPreview.app`
- **Bundle id** - Stable `dev.warp.Warp-Stable` - Preview `dev.warp.Warp-Preview`
- **URL scheme** - Stable `warp://` - Preview `warppreview://`
- **Config dir** - Stable `~/.warp/` - Preview `~/.warp-preview/`
- **Spotlight** - Stable `warp` - Preview `warppreview`
- **Brew** - Stable `warp` - Preview `warp@preview`

URL schemes are channel-specific. `warp://` always lands in Stable, `warppreview://` always lands in Preview. There is no macOS LaunchServices "default Warp" toggle that flips this. Tooling that fires Warp URIs picks the channel by scheme at call site.

Preview was made the daily driver after warpdotdev/Warp#9379 (the `tab_config` URI handler) landed - that handler shipped to Preview builds dated 2026-05-13 or later, Stable builds 2026-05-15 or later. See `warp/README.md` for the install playbook (brew install, manual `settings.toml` symlink swap, `scripts/set-warp-default-editor.sh` to rebind file-type defaults via `duti` + `lsregister`).

# Warp-owned volatile settings

`ward exec warp apply` renders `settings.toml` from `warp/templates/settings.toml.tmpl` and `ward exec warp doctor` checks the on-disk file against that same render. The default check is byte-for-byte: any difference is drift and FAILs.

A few keys break that model. The running Warp persists live UI and cloud-account state back into `settings.toml` on every launch, overwriting whatever `apply` wrote. Pinning them in the template guarantees perpetual doctor drift no matter what value the template carries.

## The volatile keys

The allowlist is `volatileSettingsKeys` in `warp/main.go`:

- `zoom_level` (under `[appearance.window]`) - Warp writes the live window zoom. The template pins a value, but Warp rewrites it to whatever the window is currently at.
- `cloud_conversation_storage_enabled` (under `[agents]`) - Warp mirrors cloud account state here on every launch, regardless of `is_settings_sync_enabled`. The only way to actually pin it false is the Warp UI toggle, which then makes Warp write `false` itself.

## How doctor handles them

For each volatile key, doctor neutralizes the key's **value** (not the line) in both the canonical render and the on-disk file before comparing, via `reconcileVolatile` / `neutralizeKey` in `warp/main.go`. A value-only difference therefore no longer counts as drift, and doctor emits a `NOTE` showing `template=<x> live=<y>` instead of a `FAIL`.

Only the scalar value is exempt. The key line itself must still be present and in place, so the template keeps emitting both keys (and `cloud_conversation_storage_enabled` keeps its documenting comment). Structural drift - a missing key line, a moved section header, a renamed key - still FAILs. The neutralization is also prefix-safe: `zoom_level` never matches a longer key like `max_zoom_level`.

## Adding a key

Add the TOML key name to `volatileSettingsKeys` in `warp/main.go`. Only do this for keys Warp genuinely owns and rewrites from live state - everything else should stay an enforced byte-for-byte match. See docs/warp.md for the original motivation.

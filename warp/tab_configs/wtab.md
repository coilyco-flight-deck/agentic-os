# `wtab`: parameterized new tabs from the shell

A pattern for opening a new Warp tab from the command line with a chosen title, ANSI tab color, and cwd. Driven by the `warp tab <color> <title>` zsh subverb (see `zsh/config.zsh` in this repo).

This doc walks the design top to bottom. If you know Warp's `tab_configs/` directory and the `warp://tab_config/<name>` URI scheme, you have all the prerequisites.

## What it does

```
$ cd ~/projects/coilysiren/repo-recall
$ warp tab cyan "🧜 repo-recall · scratch"
```

opens a new tab in the active Warp Preview window:

- Tab title: `🧜 repo-recall · scratch`
- Tab color: cyan (the ANSI cyan from your theme)
- cwd: `~/projects/coilysiren/repo-recall` (whatever `$PWD` was when you ran the command)
- Otherwise indistinguishable from a plus-button new tab: your normal shell, your normal startup, no extra processes

A few more in the wild:

```
$ warp tab magenta "session-lattice · debug"   # match the per-repo color you use elsewhere
$ warp tab red    "🔥 prod incident"            # so the angry tab is visibly angry
$ warp tab green  "🌱 fresh branch"
$ warp tab yellow "luca · readme polish"
```

`warp colors` lists the valid color set. `warp tab` with no args prints usage plus the list. Tab completion offers the same list.

## The constraints that shape it

Warp's tab config schema is in the public source at `app/src/tab_configs/tab_config.rs`. Three facts from it drive everything below.

**One.** `TabConfig` carries `name`, `title`, `color`, `panes`, `params`. The struct uses `#[serde(deny_unknown_fields)]`. Any unexpected field, anywhere, makes the entire TOML file silently disappear from the registry. Warp logs `couldn't find a tab config matching '<name>'` even though the file is on disk.

**Two.** `color` accepts `Option<AnsiColorIdentifier>`, an enum of exactly eight values: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`. Anything else fails enum deserialization, which combined with `deny_unknown_fields` means the file gets dropped entirely. There is no `pink`, `orange`, `purple`. The `color` field belongs at the top level of the file, not on a pane.

**Three.** `title` is a handlebars template against `params`. Params are filled at tab-open time, either via the UI prompt or programmatically. The URI handler at `app/src/uri/mod.rs` does NOT thread URL query params into the tab config's params. The only query param it reads is `new_window=true`. So you cannot drive `title` via `warppreview://tab_config/foo?title=bar`.

Two other things worth knowing, learned by reading the URI handler:

- Tab configs are matched by file stem, not by the `name =` field inside. `warppreview://tab_config/wtab` resolves to `~/.warp/tab_configs/wtab.toml` regardless of what `name =` says inside.
- `load_tab_configs()` is called on every URI fire. The on-disk state of `tab_configs/` at fire time IS the truth. No startup cache to invalidate.

## The shape the constraints force

You want dynamic title and color. You cannot pass them through the URL. You can put them in the TOML as literals. Warp re-reads the TOML every time. So:

**Write the TOML fresh on every invocation, then fire the URI.**

```toml
name = "wtab"
title = "scratch"
color = "blue"

[[panes]]
id = "main"
type = "terminal"
directory = "/Users/you/projects/wherever"

[params]
```

Same filename every time. Each `warp tab` call overwrites it. The shell function escapes the title and cwd for TOML basic-string rules (`\` and `"`), validates the color against the eight-value set so a typo fails fast in the shell instead of silently dropping the file, and then runs `open warppreview://tab_config/wtab`.

No commands array, no shim script, no scratch files. The tab opens directly into your normal shell, at the right cwd, with the right title and color.

## Patterns considered and discarded

**OSC 0 title pinning in a `commands` array.** Idea: leave title field empty, run `printf '\033]0;...\007'` as the first tab command. This is how `claude-dispatch-interactive` sets its title and it works there. But there, the title is a literal string baked into the TOML command. With a dynamic title threaded through a scratch file ("`printf '\033]0;%s\007' "$(cat /tmp/wtab.title)"`"), the OSC 0 fires but Warp's tab title (as shown in the vertical tabs sidebar) ends up displaying the command text, not the OSC output. The `title` field in the TOML takes precedence and is what the rest of Warp looks at.

**Pre-registered per-color TOMLs plus a runtime scratch file for title and cwd.** Eight files (`wtabred.toml`, `wtabblue.toml`, etc), each with `color =` baked in, each running a shim script that reads `/tmp/wtab.title` and `/tmp/wtab.cwd`. Title pinning had the OSC problem above. The shim also `exec`'d a new login shell to drop the user into their normal environment, which double-ran `.zshrc` and lost Warp's first-shell startup hooks. The single-file runtime-write approach makes both problems disappear.

**Color via `[[panes]]` instead of top-level.** `deny_unknown_fields` on the pane struct rejects it. File goes invisible.

**Filing a Warp feature request to thread URL params into config params.** Still worth doing for shared, multi-call use cases. Not needed for `wtab` since runtime-write already solves it cleanly.

## Why this is nice

The function is small. The pattern composes - `warp tab <color> <title>` is a one-line building block for any shell workflow that wants to spawn a parameterized tab.

The runtime-write trick generalizes. Anything where Warp's config-time-only fields need to vary per invocation can use it: dynamic `directory`, dynamic `name`, dynamic `commands`. Bake the param as a TOML literal, overwrite the file, fire the URI. The schema's `deny_unknown_fields` actually helps here: if you write an invalid value, the file goes dark and you'll see it in the Warp log immediately rather than silently misbehaving.

Failure modes are loud at the right layer. Invalid color is rejected in zsh before the URI fires. Invalid TOML is rejected by Warp with a clear log line. The tab either opens correctly with the right title and color, or it doesn't open at all.

## Files

- `~/.warp/tab_configs/wtab.toml` - the runtime-managed file. Overwritten on every `warp tab` call. Not committed.
- `zsh/config.zsh` `warp()` function `tab` subverb - the shell side.
- This file - the design doc.

## See also

- `claude-dispatch-interactive.md` next to this file - sibling pattern for the case where params are too dynamic, too large, or too structured to bake as TOML literals (a multi-line Claude prompt, in that case). Uses a pre-registered TOML plus a queue-of-JSON scratch file pattern instead.
- Warp source: `app/src/tab_configs/tab_config.rs` for the schema, `app/src/uri/mod.rs` for the URI handler.

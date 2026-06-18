# `claude-agent-work`: spawn an agent session in a new tab from a CLI

A pattern for opening a new Warp tab that runs a containerized agent against a Forgejo issue, fired from a CLI invocation: `ward agent <mode> work <owner>/<repo>#<N> --new-tab` (this repo's `ward` CLI lives at `github.com/coilyco-flight-deck/ward`). Successor to the retired `claude-dispatch-interactive` (ward#174), which ran a host `claude` in the real checkout; this one runs `ward agent <mode> work <ref>`, which clones the repo fresh inside an ephemeral container.

This doc walks the design top to bottom. If you know Warp's `tab_configs/` directory and the `warp://tab_config/<name>` URI scheme, you have all the prerequisites. A sibling doc, `wtab.md`, covers the simpler case where the dynamic params fit as TOML literals.

## What it does

```
$ ward agent claude work coilysiren/repo-recall#88 --new-tab
```

opens a new tab in the active Warp Preview window. The tab:

- prints a one-line header like `coilysiren/repo-recall#88: rotate session-lattice token format` so the tab is identifiable at a glance from the vertical tabs sidebar
- execs `ward agent claude work coilysiren/repo-recall#88`, which spins an ephemeral container, fresh-clones the repo inside it, and drops you into the agent session carrying that issue

The fan-out shape that justifies the design: queue up half a dozen issues from the couch, walk away, come back to six tabs each labelled with its issue. None of them races the others, and each runs in its own isolated container.

```
$ ward agent claude work coilysiren/repo-recall#88 --new-tab
$ ward agent claude work coilysiren/session-lattice#42 --new-tab
$ ward agent claude work coilysiren/luca#17 --new-tab
$ ward agent claude work coilysiren/eco-mods#203 --new-tab
$ ward agent claude work coilysiren/agentic-os-kai#588 --new-tab
$ ward agent claude work coilysiren/ward#274 --new-tab
# six tabs open, each in its own containerized agent session
```

## The constraint that shapes it

The payload is tiny now - just `{ref, mode, title}` - so it could almost ride in the URL. The queue survives for a different reason: **concurrency**. Two `--new-tab` fires back to back must each land in their own tab with their own payload, and Warp's URI handler does not thread URL query params into a tab config's params (`app/src/uri/mod.rs`), so the payload cannot ride the URL anyway. The CLI writes the payload to disk and the tab reads it at open time.

Other Warp-source facts that apply, same as for `wtab`:

- `app/src/tab_configs/tab_config.rs` uses `#[serde(deny_unknown_fields)]`, so an invalid TOML silently drops out of the registry.
- Tab configs match by file stem, not by the inner `name =` field.

## The flow

**One.** `ward agent <mode> work <ref> --new-tab` validates the ref (exists, open, trusted), serializes `{schema_version, ref, mode, title}` as JSON, writes it to `/tmp/ward-agent-queue/<unix-nanos>-<8hex>.json` with mode 0600, then fires `open warppreview://tab_config/claude-agent-work`.

**Two.** Warp opens the tab. The TOML's `commands` array invokes a fixed shim script (`claude-agent-work.sh`, under `warp/launch_configurations/`). Nothing in the TOML changes per spawn.

**Three.** The shim acquires a mutex (`mkdir /tmp/ward-agent-queue/.lock`, since `flock` is not portable to stock macOS), pops the oldest `.json` file by lexicographic sort (unix-nanos prefix gives FIFO), parses out `ref`/`mode`/`title` with `jq`, releases the lock, prints the self-identifying header, and `exec`s `ward agent <mode> work <ref>`. The container handles its own clone, so there is no cwd to derive.

**Four.** Soft-fail modes for every realistic failure: `jq` missing, lock unavailable for 10s, queue empty (someone opened the tab from the palette without a spawn fire), missing `ref`/`mode` fields. Each prints a one-line hint then drops the user into a plain shell.

## Why the queue, not a single scratch file

A single scratch file would work for one spawn at a time. It does not work for back-to-back `--new-tab` fires: the second `open` arrives at Warp before the first tab has finished consuming the file, and last-write-wins means one tab sees the wrong payload. The unix-nanos-prefixed queue gives strict FIFO across concurrent spawns; the mkdir mutex makes the pop atomic; the random `-<8hex>` suffix keeps two same-millisecond fires from colliding. Each tab consumes exactly one payload.

## Why this is nice

Fire and forget from the CLI side: `--new-tab` validates, writes the JSON, fires the URI, and exits. The tab opens asynchronously, so the caller can spawn ten issues at once without coordination. Identification is automatic - the header line names the issue, so ten tabs read as ten human-readable session names. The shim is forgiving: every realistic failure prints a hint and leaves a shell rather than crashing the tab. The TOML stays small; the dynamic surface lives in the JSON payload, versioned by `ward` (`schema_version`) and easy to evolve.

## Files

- `~/.warp/tab_configs/claude-agent-work.toml` - the pre-registered tab config. Static.
- `warp/launch_configurations/claude-agent-work.sh` - the shim. Reused by the launch_configuration sibling (`claude-agent-work.yaml`) and by this tab config.
- `warp/launch_configurations/claude-agent-work.yaml` - launch config variant that fires this same shim but as a new window. Used by `ward agent <mode> work <ref> --new-tab --surface window`.
- `--new-tab` source: `github.com/coilyco-flight-deck/ward`, `cmd/ward/agent_tab.go` + `docs/agent.md`, ward#174.

## See also

- `wtab.md` next to this file - the simpler sibling pattern for the case where dynamic params fit as TOML literals.
- Warp source: `app/src/uri/mod.rs` (the URI handler), `app/src/tab_configs/tab_config.rs` (the schema).

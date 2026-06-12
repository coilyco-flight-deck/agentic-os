# `claude-dispatch-interactive`: spawn a Claude session in a new tab from a CLI

A pattern for opening a new Warp tab whose payload is too dynamic, too large, or too structured to fit into a TOML literal. Used here to fire a `claude -p <multi-paragraph-prompt>` session in a new tab from a CLI invocation: `ward dispatch interactive <owner>/<repo>#<N>` (this repo's `ward` CLI lives at `github.com/coilyco-bridge/ward`).

This doc walks the design top to bottom. If you know Warp's `tab_configs/` directory and the `warp://tab_config/<name>` URI scheme, you have all the prerequisites. A sibling doc, `wtab.md`, covers the simpler case where the dynamic params fit as TOML literals. Read that first if you want the lighter pattern.

## What it does

```
$ ward dispatch interactive coilysiren/repo-recall#88
```

opens a new tab in the active Warp Preview window. The tab:

- cd's into `~/projects/coilysiren/repo-recall`
- prints a one-line header like `coilysiren/repo-recall#88: rotate session-lattice token format` so the tab is identifiable at a glance from the vertical tabs sidebar
- execs `claude -p "Work on issue coilysiren/repo-recall#88 - rotate session-lattice token format ..."`, dropping you straight into an interactive Claude session against that issue

The fan-out shape that justifies the design: queue up half a dozen issues from the couch, walk away, come back to six tabs each labelled with its issue. None of them races the others.

```
$ ward dispatch interactive coilysiren/repo-recall#88
$ ward dispatch interactive coilysiren/session-lattice#42
$ ward dispatch interactive coilysiren/luca#17
$ ward dispatch interactive coilysiren/eco-mods#203
$ ward dispatch interactive coilysiren/agentic-os-kai#588
$ ward dispatch interactive coilysiren/ward#274
# six tabs open, each cd'd into its repo, each in its own claude session
```

## The constraint that shapes it

You cannot put a multi-paragraph prompt inside a TOML's `commands` array.

You could, technically, escape the prompt string carefully enough to survive TOML basic-string rules, the shell quoting layer that Warp applies before exec, and any handlebars rendering. But the prompt body grows over time, sometimes contains backticks and quotes from issue bodies, and might want to carry JSON or YAML fragments. The "bake it as a literal" approach (used by `wtab.md`'s sister pattern) collapses under that weight.

Other things from the Warp source that also apply here, same as for `wtab`:

- The URI handler at `app/src/uri/mod.rs` does not thread URL query params into the tab config's params.
- `app/src/tab_configs/tab_config.rs` uses `#[serde(deny_unknown_fields)]`, so an invalid TOML silently drops out of the registry.
- Tab configs match by file stem, not by the inner `name =` field.

## The shape the constraints force

If the payload cannot ride in the URL and cannot fit as a TOML literal, it has to come from somewhere else on disk that the tab can read at open time. That somewhere is a scratch directory the CLI writes to and the tab reads from. The dispatch flow:

**One.** `ward dispatch interactive <ref>` resolves the ref into a payload (ref, title, cwd, prompt body), serializes it as JSON, writes it to `/tmp/ward-dispatch-queue/<unix-nanos>-<8hex>.json` with mode 0600, then fires `open warppreview://tab_config/claude-dispatch-interactive`.

**Two.** Warp opens the tab. The TOML's `commands` array invokes a fixed shim script (`claude-dispatch-interactive.sh`, lives in this repo under `warp/launch_configurations/`). The TOML itself is fixed: same color (none), same directory placeholder, same shim invocation. Nothing in the TOML changes per dispatch.

**Three.** The shim acquires a mutex (`mkdir /tmp/ward-dispatch-queue/.lock`, since `flock` is not portable to stock macOS), pops the oldest `.json` file by lexicographic sort (unix-nanos prefix gives FIFO), parses out the fields with `jq`, releases the lock, cd's into the payload's cwd, prints the self-identifying header, and `exec`s `claude` with the prompt body.

**Four.** Soft-fail modes for every realistic failure: `jq` missing, lock unavailable for 10s, queue empty (someone opened the tab from the palette without a dispatch fire), cwd does not exist. Each prints a one-line hint then drops the user into a plain shell.

## Why the queue, not a single scratch file

A single `/tmp/ward-dispatch-prompt.txt` file would work for one dispatch at a time. It does not work for the case where Kai runs `ward dispatch interactive <ref-A>` and `ward dispatch interactive <ref-B>` back to back. The second `open` arrives at Warp before the first tab has finished consuming its scratch file. Last-write-wins on the single file means one of the two dispatches sees the wrong payload.

The unix-nanos-prefixed queue gives strict FIFO across concurrent dispatches. The mkdir-based mutex ensures atomic pop. Each tab consumes exactly one payload. Two dispatches fired in the same millisecond still get distinct filenames (the `-<8hex>` suffix is random) and serialize cleanly through the lock.

## Patterns considered and discarded

**Single scratch file (`/tmp/ward-dispatch-prompt.txt`).** Fails under back-to-back dispatches as described above. The earliest version of the pattern used this and had to be rewritten to the FIFO queue once concurrent fires became routine.

**Environment variable threading.** No path. The tab's process starts from Warp's launch context, not from the dispatching shell.

**Inline prompt in a TOML written fresh per dispatch.** This is the `wtab` pattern. It works for short, well-shaped strings. For a multi-paragraph prompt body containing arbitrary issue text, the escaping burden is high and the failure modes are subtle (a bad escape makes the TOML invisible to Warp with no obvious cause). Pre-registered TOML plus a JSON queue moves the escaping into `jq`, which is built for it.

**Templating with TOML `title = "{{ ref }}"` and `commands = ["claude -p {{ prompt }}"]` plus URL params.** Would be the cleanest possible API, but Warp's URI handler does not thread URL params into config params today. Filing that upstream is reasonable. The queue pattern is the workaround that ships today.

## Why this is nice

The dispatch is fire and forget from the CLI side. `ward dispatch interactive` writes the JSON, fires the URI, and exits. The tab opens asynchronously. The caller can dispatch ten issues at once without coordination.

Identification is automatic. The header line at the top of the tab tells you which issue is running there. With ten tabs open, the vertical tab sidebar is a list of human-readable session names without any work from the operator.

The shim is forgiving. Every realistic failure mode prints a hint and leaves you in a shell rather than crashing the tab. `jq` not installed, queue mutex stuck, queue empty, cwd missing - all soft-fail with a recovery line.

The TOML stays small. A pre-registered file plus a single command line, no per-dispatch state. The dynamic surface area lives in the JSON payload format, which is versioned by `ward` and easy to evolve.

## Files

- `~/.warp/tab_configs/claude-dispatch-interactive.toml` - the pre-registered tab config. Static.
- `warp/launch_configurations/claude-dispatch-interactive.sh` - the shim. Reused by the launch_configuration sibling (`claude-dispatch-interactive.yaml`) and by this tab config.
- `warp/launch_configurations/claude-dispatch-interactive.yaml` - launch config variant that fires this same shim but as a new window. Used by `ward dispatch interactive --surface window`.
- `ward dispatch interactive` source: `github.com/coilyco-bridge/ward`, see issues #270, #279, #280 for the design discussion.

## See also

- `wtab.md` next to this file - the simpler sibling pattern for the case where dynamic params fit as TOML literals.
- Warp source: `app/src/uri/mod.rs` (the URI handler), `app/src/tab_configs/tab_config.rs` (the schema).

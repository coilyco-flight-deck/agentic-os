# The native agent terminal

`aterm` opens the window a native agent session runs in. The status-line composer that fills the rows inside it is documented with the image that bakes it, in [in-container agent identity](dev-base-agent-identity.md).

## `aterm`

`aterm` opens one composed agent session in its own branded kitty window. It is the windowed sibling of the `acompose` shell function, runs the same runtime of a leased shadow wrapping `agent-compose launch`, and leaves the terminal you typed in free. Name a role without a seat and both take the agent from [`harness-launch-profiles.yaml`](../.agents/harness-launch-profiles.yaml), which `aos` owns and both ask, so neither carries a second parser.

```text
aterm                              # pick a role, then a seat
aterm platform                     # the role's default seat
aterm platform codex -- --resume   # arguments for the harness
aterm --list                       # the live roster, no window
aterm --list --json                # the same roster, for a script
```

The window opens maximized at font size 14.5, which `--start-as` and `--font-size` override, since kitty's own default of 11.0 is set for a terminal rather than a session you read all day. It needs `agent-compose` and kitty on `PATH` and bundles neither. Without `aos` it still launches, unleased. `--dry-run` prints the plan and opens nothing. `--list --json` prints the launchable projection, every live role carrying only the seats `agent-compose launch` can start, under contract `aterm.roster.v1`.

**It refuses a stale role before it opens anything.** Role slugs turn over, so `aterm` reads `agent-compose catalog roles --json` on every run and names the live roster in the refusal. A transposed `platform` comes back as `is not a live role. Did you mean platform?` plus every live slug and display name. A seat is checked twice: it has to belong to the role, and to be a harness `agent-compose launch` can start. A catalogue seat like `penpot` is real but not launchable, and the refusal says which of the two it failed.

**Tab completes from the same roster.** `aterm <TAB>` offers the live slugs, `aterm sysadmin <TAB>` only that role's launchable seats, so a slug that turned over stops completing rather than completing into a refusal. The read is under 10ms, so no cache can go stale. `shell/common.sh` registers bash and zsh through `aterm completion <shell>`, after `compinit` in zsh. A missing `agent-compose` yields silence, never a diagnostic mid-keystroke.

**A slow pre-flight names itself.** `aterm` shells out for a seat, roster, and overlay before it opens anything, and captures their output, so a wrapped `aos` converging the host first presented as a launcher that had stopped. After two seconds `aterm` names the command it waits on.

**A failing launch stays on screen.** A terminal closes the window the moment its child exits, so a failed launch used to vanish before anyone could read why. `aterm` runs the child through its own `_session` stage rather than handing the harness to kitty directly. That stage passes the exit code through and holds the window on any non-zero exit, and `--hold` also holds after a clean exit. The launcher watches for a startup failure, so "no window appeared" names its cause.

**The title leads with what separates two windows.** A window manager truncates near 30 characters, so segments run workspace, task title, role, glyphs and seat name, expression. The workspace is `repo@branch` for the checkout `--working-directory` names, left out when that is the default projects root.

**`--dry-run` reads for a person, and failures split by code.** The default renders the identity, workspace, both brand colors as swatches, each personality in its own color, and the child argv. `--dry-run --json` keeps the machine plan that `scripts/check-aos-release.sh` asserts against. Exit codes: 2 usage, 3 off-roster role or seat, 4 a dependency missing from `PATH`, 5 the window failed to open, 1 anything else, and a child's own code passes through.

**The picker follows the terminal, not stdout.** `aterm > log` used to refuse with "a role is required", because the check wanted stdin and stdout both to be character devices. The form runs on `/dev/tty` instead.

**`aterm doctor` preflights the whole chain**, exits 1 on a broken link, and names the unleased-shadow case a launch makes silently. `--json` is `aterm.doctor.v1`.

**It decodes the whole identity overlay.** `agent-compose overlay --json` ships a complete sensory identity per personality, and a struct naming fewer fields drops the rest in silence. `aterm/overlay.go` declares every leaf, and `TestOverlayDecodesEveryShippedField` fails on any that does not survive a round trip. Only the glyphs and `favorite_color` reach the window today.

## macOS app bundles

`aterm bundles` writes one `.app` per live role into `~/Applications`, so a role opens from Spotlight, the Dock, or Finder with no terminal to type in. Each is a wrapper around `aterm <role>`, so the window it opens is the one above.

```text
just aterm-bundles                     # write them
just aterm-bundles --dry-run           # what would land, rendered
just aterm-bundles --dry-run --json    # the same plan, for a script
just aterm-bundles --icon path.icns    # one shared icon for every bundle
```

**A Finder launch carries none of your shell's PATH.** It starts at `/usr/bin:/bin:/usr/sbin:/sbin`, where neither `aos`, `agent-compose`, nor kitty lives, so generation resolves all four binaries once and pins them through the env vars `aterm` already reads. Pinning those four is not enough on its own: `agent-compose launch` resolves the harness off `PATH` itself, so a bundle that only pinned them reached shadow init and then died on `claude` not found. The wrapper rebuilds `PATH` from a login shell, which stays current as tools move, and falls back to the generation-time copy when a profile exports none.

**The wrapper claims no Dock tile of its own.** It exits as soon as `aterm` detaches the window, so a tile for it would flicker while the session it opened keeps running. `LSUIElement` leaves the kitty window as the only visible result, and the bundle stays pinnable and searchable regardless. A launch that fails before a window opens has nothing on screen to hold the error, so the wrapper shows it in an `osascript` alert rather than exiting into nothing.

**A bundle is named for who answers.** `Claude // Vera // Systems Administrator` is what the Dock shows, and a POSIX filename cannot hold a slash, so the name is stored with ` :: ` and macOS renders each colon as one. Nothing clips it: the limit is 255 bytes, though Finder and Launchpad wrap a name this long across two lines. Only the bundle directory carries it, since the executable inside is a plain `aterm-<role>`.

**Roles come from the live roster**, the same read the launcher and its completion use, so no second list of roles exists to go stale. A bundle is recognized as ours by a marker inside it rather than by its name, so a renamed scheme reports what the last run wrote instead of orphaning it. What this run no longer writes is reported rather than deleted, an app this command did not write is never overwritten, and every target is checked before any is written, so a refusal cannot half-regenerate the set. Bundles are per-role, taking the seat from the launch profiles, and each click opens a new session rather than focusing a running one.

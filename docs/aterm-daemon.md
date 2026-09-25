# The aterm host daemon

`aterm daemon` owns the terminal of every session `aterm` opens. The kitty
window is one client attached to it, and `aterm send` types a stamped message
from one session into another. It replaced VibeTunnel. The window it serves is
[the native agent terminal](aterm.md). Records: teable:coilyco/agentic-os#8219
(send) and teable:coilyco/agentic-os#8220 (daemon and client).

```text
aterm agents                          # live sessions, the targets send takes
aterm send frontend-eng "ready for review"
aterm send --launch scientist -       # open the role if none answers, body on stdin
aterm attach eng-platform-beetle-ox   # another terminal on a live session, Ctrl-] detaches
aterm daemon                          # foreground, websocket on 127.0.0.1:7419
aterm ask "Ship it?" yes no           # a choice card on Kai's client
aterm mcp                             # list_agents, send_message, ask_choice
```

## What the daemon owns

**`_session` hands the harness to the daemon instead of running it.** After the card, `_session` sends a `spawn` carrying the argv, its environment, directory, and window size, then attaches as one client. The argv reaches the harness untouched, the shadow child's own `--` included, and the window still holds on a non-zero exit.

**A session is named `<role>-<identity>-<code>`, and a spawn under a live session's name is refused.** The code comes from `aos _session-id` and goes to the shadow as `--session-id`, so it doubles as `AOS_NATIVE_SESSION` unless taken. Two instances of one role run side by side, and an aos that cannot mint leaves the name unsuffixed. For the claude seat aterm passes the name as `--name` too, unless the caller named it or set `--no-stable-name` (`ATERM_NO_STABLE_NAME`).

**The harness starts without agent-compose's Enter gate.** The window drew its own card, and a daemon launch has nobody at it, so `_session` sets `AGENT_COMPOSE_NO_PAUSE=1`. It also flushes unread terminal input before attaching, since a reply to the card's color query arrives there and would read as Kai typing. agent-compose's `ESC ] 7750 ; agent-compose ; degraded=<steps> BEL` becomes the session's `degraded` field.

**A session outlives its window.** Closing the window detaches that client, and the harness keeps running until it exits. `aterm attach` reattaches from any terminal with the last megabyte of output replayed, minus terminal queries it would answer again.

**A missing daemon costs messaging, never the session.** `_session` starts the daemon when none answers. Failing that, it runs the harness directly. `aterm doctor` reports a `daemon` row, which is a warning only when the socket directory would be refused.

**The socket is `/tmp/aterm-<uid>/daemon.sock`, keyed by uid rather than `HOME`**, because a session shadow moves `HOME` and every seat must reach one daemon. `ATERM_DAEMON_SOCKET` overrides it. The directory must be owned by the user and closed to others, and that permission is all of local client auth. An idle daemon exits after five minutes, so the next launch runs the upgraded binary.

## `aterm send`

**The sender is stamped by the daemon, never declared.** Each spawn gets a fresh `ATERM_SESSION_TOKEN` in its environment, replacing any inherited one. `send` presents it, and the daemon resolves it to the seat and types `[from <role> <identity>] <body>`. A token the daemon did not issue exits 2. Text a person types carries no envelope.

**A body cannot forge a second envelope.** A body line opening with `[from `, after leading space, gets a `\` in front. Every C0 control byte but tab, DEL, and C1 control is written in caret or `<U+XXXX>` notation, since an escape byte would end a bracketed paste and send the rest as keys. The client marks stamped rows by matching the envelope, so this escaping is required.

**Targets resolve in tiers**: exact session name, then role slug, then identity, then harness. The first tier with a match wins, several matches in it refuse and name them, and none exits 3 with the live sessions listed. `--launch` on a role slug opens the role through `aterm <role>` and holds the message up to three minutes for it.

**Delivery serializes with the keyboard.** One lock covers every PTY write, so a message never interleaves with keystrokes. A message is `queued` until the target is ready, `held` while Kai typed in the last 1.5 seconds or has a draft touched in the last minute, then `delivered` or `failed`. Enter, Ctrl-C, or Ctrl-U clear the draft, and a held message lands after it.

**A program that asked for bracketed paste gets the message as one paste, then Enter 300ms later**, since a TUI reading a paste as a burst takes an Enter that arrives with it as a newline. Without bracketed paste, lines are joined with spaces so a newline cannot submit early. The daemon reads the mode from the program's own output.

**A process inside a session cannot type into one.** The daemon reads the connecting pid from the kernel and walks its parents. Such a process may send, stamped, but not type, unless it spawned that session. It guards against mistakes, not a same-user process that double-forks out.

## Per-harness delivery

Observed on 2026-09-25 in real aterm windows: a claude seat sent to a codex seat, and codex answered back, each `delivered` within seconds.

* **claude, codex v0.156.1** - both turn bracketed paste on at their prompt and take the stamped message as one paste, submitted on the delayed Enter. Codex's shell rebuilds `PATH` from a login shell, so it runs the Homebrew `aterm`. Mid-turn queuing is unverified for codex.
* **goose, opencode** - unverified. They fall back to ready after 30 quiet seconds.

**Ready means bracketed paste for claude and codex, never a quiet screen**, since a gate or a slow start is quiet too.

## Wire contract

`aterm.daemon.v1` is one JSON object per line over the socket, and one per text message over the websocket. Both sides open with `hello` and `welcome` naming the format, and a mismatch refuses. Requests carry an `id` echoed on the reply or on an `error` with `code`.

* `spawn`, `attach` (optional `replay`), `detach`, `input` and `output` (base64 `data`), `resize`, `exit` with `code`.
* `send` answers `sent` with the message state, waiting up to 3 seconds for delivery.
* `list` answers `sessions`. `subscribe` to channel `sessions` pushes the roster on every change, and `message` events carry each state change, never the body, which only the target's terminal receives.
* `whoami` resolves a token to its session. `roster` answers with `aterm.roster.v1`, the launchable roles `aterm --list --json` prints, read fresh per request. `launch` with a `role` and optional `seat` opens it as `aterm <role> [seat]` would, answering `launched`.

* `ask` (from `aterm ask` or the `ask_choice` MCP tool) takes a `question`, `options` of `label` and `description`, `header`, `allow_other`, and `multi`. The daemon stamps the asker from its token and pushes `ask` to subscribers, replayed on subscribe. A client's `answer` (`ask_id`, `picks`, `text`) or `cancel_ask` settles it, and `asked` tells every client to drop the card. An asker leaving cancels its asks, and 15 minutes times one out. An answer is Kai's input, so it takes the typing guard.

**Browsers get the client from `--client-dir` (`~/.local/share/aterm/client`) at `/`, and a websocket there.** Loopback is `127.0.0.1:7419` (`--websocket`), refusing a non-loopback Host or Origin. The tailnet is HTTPS on this node's tailnet name, port 7419 (`--tailnet-port`, empty for none), certified by `tailscale cert`. `tailscale whois` admits a peer, never the request: this node owner's untagged device, or one tagged `tag:physical` (`--allow-tags`), mirroring the tailnet's physical-to-physical SSH grant. A websocket opens only from the page the daemon served or `https://coilyco.dev` (`--allow-origins`).

## Not built yet

The MCP Apps gateway and the streamed browser, on teable:coilyco/agentic-os#8220.

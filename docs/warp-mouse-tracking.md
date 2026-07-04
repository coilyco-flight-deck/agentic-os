# Warp mid-director mouse-tracking escape hatch

A recovery for a stuck xterm mouse-tracking flood inside a running warded director, without killing the director. See [warp.md](warp.md) for the config module this rides on, and #320 for the investigation.

## The failure

A warded director session (Claude Code, an Ink TUI, hosting child commands) can be poisoned by a child (a Linux tool under WSL, an Ink CLI) that enables xterm mouse-tracking mode 1003 and exits without restoring it. The Warp pane then floods with raw `^[[<35;X;YM` SGR motion reports (the `35` byte is 32 for motion + 3 for no button, which only mode 1003 emits). Nothing consumes the reports, so the pane fills with noise.

## Why the pwsh-prompt reset cannot heal it

The origin fix (commit `b562b4f`, `fix(warp): reset stuck mouse-tracking modes in pwsh prompt`) chains the outer host pwsh prompt to emit `ESC[?1000l..1006l` before each prompt, so a dirty-exiting child self-heals on the next prompt. Mouse-tracking (DECSET 1003) is state held in the Warp emulator - it only clears when a process writes DECRST bytes into the terminal output stream. A shell emits those only when it draws a prompt, and while the director TUI holds the terminal no prompting shell runs. The layers:

```
Warp pane -> pwsh (outer) -> Claude Code TUI (director) -> WSL/Ink child that dirties 1003
```

The child dirties the mode and returns control up to the director, which never yields to a prompt. The outer pwsh prompt only fires once the whole director exits - hence, historically, "drop the TUI." A precmd hook in the inner shell would fail the same way (the director sits between it and the pane), and a Warp keybinding that "sends text" writes the director's stdin, the wrong direction, and cannot reset the emulator.

## The fix: an emulator-level toggle keybinding

`warp apply` renders `keybindings.yaml` (a layer-2 rendered file, sibling of `settings.toml` in the config dir) with one managed binding:

```yaml
"workspace:toggle_mouse_reporting": "ctrl-shift-m"
```

`workspace:toggle_mouse_reporting` flips mouse reporting at the **Warp emulator layer** with zero cooperation from the director or any child. Press `ctrl-shift-m` while the flood is happening and it stops, TUI still running. This is the "reset without dropping the director" recovery.

It is a **toggle**, not a one-way disable: one press clears a stuck-on flood, a second press re-enables legit TUI mouse use. That is fine for an escape hatch.

The binding rides `warp apply` / `warp doctor` to every host, the same as `settings.toml`. `keybindings.yaml` did not exist on the Windows tower before this (zero custom bindings), so there was nothing to conflict with.

## Correct-layer note

The genuinely correct fix is upstream: the director TUI (Claude Code) re-asserting mouse state on redraw. That is not ours to patch. This keybinding is a mitigation.

A second lever was investigated and deferred: a dev-base `BASH_ENV`/EXIT-trap self-heal that emits DECRST on each `bash -c` teardown. It is mechanically easy but risky - a naive `printf` to stdout would inject escapes into Claude Code's captured command output fleet-wide, so it must emit to `/dev/tty` guarded by `[ -t 1 ]`, and that guard may mean it never fires for pipe-backed children (exactly the ones that matter). Blast radius vs uncertain payoff, so it needs an empirical spike of a live director session before it lands. Tracked as follow-up to #320.

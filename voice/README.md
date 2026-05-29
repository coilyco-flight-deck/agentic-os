# voice/ - Wispr Flow auto-submit

Tools that press Enter for you after a Wispr Flow dictation, so dictating into a
prompt box auto-submits. Three implementations, split by how the dictation *ends*.

## The family

* `../hammerspoon/init.lua` - macOS, push-to-talk - arms when you release the Wispr
  hold (`fn`), fires Enter when the next clipboard paste lands. Warp-frontmost only.
* `../autohotkey/wispr-auto-enter.ahk` - Windows, push-to-talk - same idea, arms on
  releasing Left Ctrl+Left Win (or Left Alt), fires Enter on the next clipboard change.
* `vad-daemon.py` - Windows, **hands-free toggle** - the piece the other two can't
  cover.

**Why the daemon exists.** The clipboard tools arm on the *release* of a push-to-talk
hold. Wispr hands-free mode is a toggle (Ctrl+Win+Space to start, again to stop) - there
is no release gesture to arm on. So the daemon supplies the missing end-of-dictation
signal itself: it watches the raw mic with [silero-vad](https://github.com/snakers4/silero-vad),
and after about two seconds of silence following speech it fires the Wispr toggle-off
chord and then Enter. You stop talking, the prompt sends. Hands never leave where they were.

## Architecture

A launcher (VoiceAttack, a hotkey script, anything) opens a Wispr hands-free session and
signals the daemon `start` over local UDP. The daemon opens the raw hardware mic, runs
silero-vad per 32ms frame, and on a silence-after-speech window fires Ctrl+Win+Space then
Enter, then closes the mic. It idles until the next `start`.

**The mic is open only during a session.** `start` opens the stream, commit/cancel closes
it. At rest the daemon holds torch in RAM and a UDP listener, but the mic is released and
the OS in-use indicator is dark - so it is cheap to leave running on login (see below).

UDP messages on `127.0.0.1:5555`:

* `start` - begin watching (resets VAD state, drops pre-signal audio)
* `cancel` / `stop` - abort: toggle Wispr off, no Enter
* `go` - commit immediately, bypassing the silence wait (impatient send)

## Setup

torch has no wheels for the system Python 3.14, so the daemon runs in its own pinned
3.12 venv. `setup-venv.ps1` builds it (routed through coily, since the repo lockdown
denies bare uv):

```powershell
powershell -ExecutionPolicy Bypass -File setup-venv.ps1
.venv\Scripts\python.exe vad-daemon.py --list-devices    # find your raw hardware mic
.venv\Scripts\python.exe vad-daemon.py --device "<index-or-name>"
```

First run downloads silero (~25MB) via torch.hub, then it is cached. Set `--device` to
the **raw hardware mic**, not Krisp's virtual device - silero handles noise natively, and
watching raw audio sidesteps the Krisp-artifact problem.

## Run on login (Windows Task Scheduler)

Because the mic is dark at rest, it is cheap to keep the daemon resident. `register-task.ps1`
adds an AtLogOn task that launches it hidden in your interactive session (it has to run as
you, not SYSTEM - it needs the mic and types into the active desktop):

```powershell
setx VAD_DEVICE "<index-or-name>"                         # so the task picks the right mic
powershell -ExecutionPolicy Bypass -File register-task.ps1
Start-ScheduledTask -TaskName vad-daemon                  # start now, no reboot
```

`run-vad-daemon.ps1` is the launcher the task invokes (also runnable by hand). It reads
these env vars and writes `vad-daemon.log` (daemon runtime) + `launcher.log` (wrapper)
next to itself:

* `VAD_DEVICE` - mic index/name (set yours with `setx`).
* `VAD_THRESHOLD` - speech-probability cutoff. Defaults to **0.3**, tuned to the raw Razer
  mic: silero reads its ambient hum at ~0.0 and soft syllables dip to 0.3-0.4, so the
  stock 0.5 commits early mid-sentence. Retune with `--probe` (see below).
* `VAD_SILENCE` - silence-timeout seconds. Unset uses 1.8; raise to ~2.2 if you pause to
  think mid-dictation and get cut off.

Remove the task with `Unregister-ScheduledTask -TaskName vad-daemon`.

### Tuning against your noise floor

`--probe` opens the mic and logs silero's live speech probability without pressing any
keys. Sit silent to read your floor, then talk to see the peak; set `VAD_THRESHOLD` into
the gap (comfortably above the floor, below your softest speech):

```powershell
.venv\Scripts\python.exe vad-daemon.py --device 1 --probe
```

Not on Windows? The daemon still runs and logs the keystrokes it *would* send (dry-run),
so you can tune VAD detection on any machine. Only the actual key presses are Windows-only.

## VoiceAttack wiring

In the "hey claude" command, after the existing Ctrl+Win+Space keypress add:

* Other -> Execute External Program
* Program: `powershell.exe`
* Arguments: `-NoProfile -Command "$c=New-Object Net.Sockets.UdpClient; $b=[Text.Encoding]::UTF8.GetBytes('start'); $c.Send($b,$b.Length,'127.0.0.1',5555)"`

Send `cancel` or `go` the same way from a "scratch that" / "go" phrase to wire the abort
and override gestures.

## Tuning

All knobs are flags, so iterating never means editing the file:

* `--silence-timeout` (default 1.8s) - too short rushes you, too long breaks flow. Raise
  to ~2.2 if it commits on natural thinking pauses, drop to ~1.5 if the lag feels heavy.
* `--vad-threshold` (default 0.5) - speech probability 0-1. Raise to 0.6-0.7 if it commits
  mid-sentence on long pauses.
* `--commit-delay` (default 0.15s) - pause between the toggle-off chord and Enter, so
  Wispr's paste lands before the submit. Raise if Enter sometimes fires into an empty box.
* `--verbose` - logs per-frame speech probabilities, the fastest way to pick a threshold.

Suggested loop: start at the defaults, smoke-test five prompts, then adjust one knob at a time.

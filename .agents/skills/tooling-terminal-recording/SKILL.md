---
name: tooling-terminal-recording
description: Record a terminal as a GIF or video without a live take. VHS for deterministic commands, asciinema for sessions whose timing cannot be predicted. Use when producing a demo, README asset, or social clip from CLI output.
compatibility: Requires `vhs`, `asciinema`, and `agg`. VHS also pulls `ttyd` and `ffmpeg`.
metadata:
  source-url: https://github.com/charmbracelet/vhs
---

# Terminal recording

The agent never performs a live take. Timing, retakes, and the operator's
attention are all removable from the critical path, and removing them is the
point of both tools here.

## Choosing the tool

VHS renders a `.tape` script to GIF, MP4, or WebM with no live session. It suits
any command that is fast and deterministic. A wrong pause is an edit to a number
rather than another take.

asciinema records a real session to a text cast. It suits anything whose output
timing cannot be known in advance, which includes every agent session, since
responses vary by tens of seconds. `agg` converts a cast to GIF.

## Measure before choosing dimensions

1. The agent measures the widest line the command emits, because that number
   dictates every other setting:

   ```text
   COMMAND | awk '{print length}' | sort -rn | head -1
   ```

2. The agent converts columns to pixels at roughly `0.83 * FontSize` per column,
   then picks `Set Width` to fit the measured width without wrapping.
3. The agent checks the resulting aspect ratio against the destination. Output
   past about 120 columns yields a letterbox strip that suits a README banner
   and fails on a social post. When the ratio will not work, the fix is a
   narrower command rather than a smaller font: pipe through `head` and `cut`,
   or record a different subcommand.

## Recording a live session

The agent records with an idle cap so the operator does not have to be quick,
attentive, or uninterrupted while the recording runs:

```text
asciinema rec -i 2 demo.cast
agg demo.cast demo.gif
```

Every pause longer than the `-i` value clamps to that value on playback. The
cast stays plain text with per-event timings afterwards, so pacing remains
editable long after the session.

## Verify the frames

Exit zero from `vhs` means a file was written, not that the file is legible. The
agent extracts a frame and looks at it before reporting a render as good:

```text
ffprobe -v error -show_entries format=duration -of csv=p=0 OUT.gif
ffmpeg -v error -ss SECONDS -i OUT.gif -vframes 1 frame.png -y
```

Wrapping, scrolled-off content, and mid-token `cut` damage are all invisible in
the exit code and obvious in the frame.

## Showing the result to a human

macOS Preview steps an animated GIF frame by frame rather than playing it, so
the agent opens rendered output in a browser. Several clips go on one local HTML
page rather than several tabs.

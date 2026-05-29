# Tracky Mouse

Pointer to the cursor / HUD work that the [VTuber pet](vtuber-pet/) sits next to and must cohere with. Tracky Mouse is the head-tracking mouse + gaze HUD (targeting reticle, edge-to-edge crosshair, click-fire feedback) that drives the hands-free cursor.

## Repo

- **Source** - https://github.com/coilysiren/tracky-mouse
- **Workspace checkout** - a sibling repo in Kai's coilysiren tree at `coilysiren/tracky-mouse`, not vendored into this repo.
- **Current branch** - `main`.

## Why it lives in the pointer, not vendored here

The cursor and the pet are one design language but two repos with separate release cadences. This file is the durable cross-reference so a session working the pet knows where the current Tracky Mouse work is without spelunking the workspace.

## Engineering learnings the pet inherits

These were paid for by the Tracky Mouse HUD and transfer straight to the pet:

- **State by silhouette and motion, not hue** - reactions must differ in shape and movement, never just color.
- **Loud enough for peripheral vision** - feedback that feels right on close inspection is too subtle in practice. Bigger scale, longer linger, stronger glow.
- **Per-frame work must be cheap** - anything cursor-following has to be CSS-variable driven and frame-coalesced or it saturates the compositor and jitters the whole screen.

The cursor's **style** (the sparkly fantasy reticle) is no longer the visual baseline for the pet. The shipped icon trio is. The engineering learnings above still hold.

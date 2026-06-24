# Disk-footprint tracker

A project-local status-line row that surfaces how much disk a repo is using and how much it has grown, so build artifacts, caches, and `.git` bloat that accrete between cleanups stop sneaking back onto disk unnoticed.

This repo dogfoods the [second status-line row](features-agents-sessions.md) hook with [`.agentic-os/statusline.sh`](../.agentic-os/statusline.sh). `scripts/agent-name.sh` runs that hook when present and appends its stdout as a second row under the agent name.

## What it shows

A single row like `📦 disk 412M  ▲ +38M/3d`:

- **size** - `du -sk` of the whole working tree, including `.git` and untracked or ignored files (the caches and build output that actually do the sneaking).
- **delta** - signed growth since a persisted baseline, with the baseline's age. `▲ +38M/3d` means the tree grew 38M over the 3 days since the baseline was anchored. `▼` marks a shrink, `•` marks flat.
- **color** - green when flat or shrank, yellow for mild growth, orange past `AOS_DISK_WARN_KB`, bold red past `AOS_DISK_CRIT_KB`.

## How it stays cheap

The status line refreshes often, and `du` over a large tree is not free. So the hook never runs `du` on the foreground path after the first reading:

- State lives under `~/.cache/agentic-os/disk/`, keyed by a hash of the repo path: `<key>.current` (`<epoch> <size_kb>`) and `<key>.baseline`.
- Each invocation reads the cached `.current` and prints instantly.
- When the cached reading is older than `AOS_DISK_REFRESH_SECS`, the hook kicks a background `du` (guarded by an atomic `mkdir` lock, with a stale-lock breaker) that updates `.current`. Only the very first run for a repo measures synchronously, since there is nothing cached to show yet.

## Baseline and re-anchoring

The baseline persists across sessions and reboots, so growth tracks over days rather than resetting each session. After an intentional cleanup (pruning `node_modules`, `git gc`, clearing a build dir) delete the per-repo `.baseline` file to re-anchor:

```sh
rm -f ~/.cache/agentic-os/disk/*.baseline
```

The next reading becomes the new baseline.

## Tunables

All env-overridable, with defaults:

- `AOS_DISK_REFRESH_SECS` - min seconds between background `du` runs (`120`).
- `AOS_DISK_WARN_KB` - growth that turns the row orange (`51200`, +50M).
- `AOS_DISK_CRIT_KB` - growth that turns the row bold red (`256000`, +250M).

## Reuse in another repo

The hook is self-contained and resolves its own repo root, so any repo can adopt it: copy `.agentic-os/statusline.sh` into the target repo (or symlink it), mark it executable, and `scripts/agent-name.sh` picks it up for sessions rooted there.

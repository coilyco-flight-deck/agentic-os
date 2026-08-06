# Native startup narration

Native startup runs several seconds of local Git and remote fetch work before
the harness takes the terminal. It announces each phase on stderr before that
phase runs and reports the phase's elapsed time when it ends, so the wait is
attributable rather than silent. Owner:
[native agent workspaces](native-agent-workspaces.md).

## What a launch prints

```text
aos: launch   native claude startup
aos: start    converge environment
aos: done     converge environment 0.18s (0 catalogues, 12 MCP servers)
aos: start    reclaim finished sessions
aos: done     reclaim finished sessions 0.31s (4 live worktrees)
aos: start    fleet pass over 19 repositories
aos: fetch    1/19 coilyco-flight-deck/agentic-os
aos: fetch    2/19 coilyco-flight-deck/ward
aos: done     fleet pass over 19 repositories 14.8s (slowest coilyco-bridge/deploy 2.10s)
aos: start    link 19 session worktrees
aos: worktree 1/19 coilyco-flight-deck/agentic-os
aos: done     link 19 session worktrees 1.10s (19 linked)
aos: ready    native startup 16.2s (fleet pass 14.8s, link 19 session worktrees 1.10s)
aos: exec     agent-compose
```

The per-repository `fetch` and `worktree` lines print before their command
runs, so a stalled remote names the checkout it is stuck on. Each looping
phase closes by naming its slowest item, which turns a long phase into one
attributable repository.

## Reading the closing lines

`ready` totals the run and ranks the phases that took at least a tenth of a
second. Instant phases stay out of that list, so the line names the cost
instead of restating the pipeline. `skip` explains a phase that did not need
to run, which is how a fast startup accounts for itself: the ten-minute fleet
pass skips most launches.

`exec` marks the boundary. Waiting after that line belongs to Agent Compose or
the harness, not to AOS.

## Waiting on the startup lock

Startup cleanup is serialized by a lock directory under the native state root.
The lock records the PID and process-start identity of the launch holding it,
so a launch interrupted mid-cleanup is reclaimed by the next launch at once
rather than blocking it. Reclaiming prints `wait  reclaiming startup lock
abandoned by pid N`.

A genuinely live holder is never stolen from. The waiting launch reports the
holder's PID every five seconds and gives up after two minutes with an error
naming that PID and the lock path, so the terminal always says who to wait for.

## Volume

`AOS_NATIVE_PROGRESS` selects how much reaches stderr.

* `steps` - the default. Every phase, every loop item, and the total.
* `summary` - the `ready` total alone.
* `debug` - adds the launch command and internal notes.
* `off` - restores silence.

Warnings and errors ignore the setting and always print.

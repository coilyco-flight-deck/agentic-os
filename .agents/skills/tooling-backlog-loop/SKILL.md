---
name: tooling-backlog-loop
description: Drive a whole repo backlog to done with a supervised ralph loop - dispatch headless agents on the headless lane, surface interactive issues to the human, poll for outcomes, and unblock stuck agents by posting guidance back to the issue. Triggers - backlog loop, ralph loop, burn down the backlog, supervised dispatch, maniacal automation, dispatch agents across the backlog, unblock the agents, drive the queue, auto-burndown, multi-repo scope.
---

# Backlog loop

A guided foreground loop that drives a repo's open backlog to done. You are the supervisor: the deterministic parts are `ward exec backlog-loop` verbs, the judgment (unblocking a stuck agent, talking with the human) is yours. The supervised foreground form of the heartbeat loop (agentic-os#237).

The backbone `scripts/backlog-loop.py` runs as `ward exec backlog-loop -- <verb>`. It reads the tier (`P0`-`P4`) and mode (`headless`/`interactive`/`consult`) labels `ward exec goose-triage` wrote - it does not recompute them. State lives in a durable ledger under `~/.cache/agentic-os/backlog-loop/<repo>.yaml`, so the loop survives a restart.

## Scope: span many repos at once

When work spans repos, drive them as a **scope**: `--repo a/b,c/d` makes `select` / `next` / `poll` aggregate one ranked view across the set (agentic-os#279). Per-issue verbs take a bare `<num>` or an `<owner/name>#<num>` ref. See [docs/backlog-loop-scope.md](../../../docs/backlog-loop-scope.md).

## The lanes

- **headless** - tier + `headless`. The auto-burndown lane you dispatch (narrow by design).
- **interactive** - tier + `interactive`. Surface to the human to hand-drive; never auto-dispatched.
- **consult** / **untriaged** - held. consult needs a human design call; untriaged is missing a label.

## The loop

1. **Select** - `backlog-loop -- select --repo <owner/name>` refreshes the ledger and prints the lanes; re-running mid-loop never clobbers in-flight state. A non-empty untriaged lane nudges you; `select --triage` folds `ward exec goose-triage` in first (whole scope) so the loop owns its inputs.
2. **Surface interactive** - read the top interactive issues to the human as one-liners to hand-drive.
3. **Dispatch headless** - for each queued headless issue, a few at a time: `backlog-loop -- dispatch <num>` posts the protocol comment, runs `ward agent headless`.
4. **Poll** - `backlog-loop -- poll`. For each dispatched issue whose container exited, reads its `WARD-OUTCOME:` comment into `done`/`blocked`/`failed`. Re-poll until drained.
5. **Unblock** - for each `blocked` issue, surface the blocker, get the answer, `backlog-loop -- unblock <num> --note "<guidance>"` to post it and re-queue.
6. **Re-dispatch** and repeat 4-6 until the headless lane is `done`/`failed`. Report.

## The outcome protocol

A dispatched agent ends with a final comment whose first line is `WARD-OUTCOME: done` / `blocked - <what it needs>` / `failed - <why>`, candid retro below. `poll` parses that line. v1 injects it as a dispatch-time comment the agent reads into its seed.

## Verbs

- `select [--limit N] [--triage]` - refresh the ledger, print lanes; `--triage` triages the scope first, then re-selects.
- `next --lane headless|interactive [--count N]` - next actionable issues as JSON (blocked first).
- `dispatch <num>|<owner/name>#<num> [--no-preflight] [--force] [--dry-run]` - launch a headless agent; `--force` re-dispatches past a lingering reservation.
- `poll` - reconcile dispatched issues against `docker ps` + outcomes.
- `unblock <num> --note "..."` - post guidance + re-queue.
- `outcome <num>`, `mark <num> --state <s>`, `status`.

## Cautions

- Dispatch a handful at a time and poll between batches, never the whole lane at once.
- An exited container with no `WARD-OUTCOME` stays `dispatched` and is flagged - read its log before retrying.

See [docs/backlog-loop.md](../../../docs/backlog-loop.md) and [tooling-issue-prioritization](../tooling-issue-prioritization/SKILL.md).

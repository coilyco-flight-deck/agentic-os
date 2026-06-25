# Backlog loop

`ward exec backlog-loop` is the programmatic backbone for a **supervised ralph loop** over a repo's open backlog. A human-guided foreground loop dispatches headless agents across the backlog, surfaces their blockers, takes the human's unblock guidance back to the issue, re-dispatches, and repeats until the headless lane is drained. It is the foreground form of the heartbeat loop (agentic-os#237), consuming the automation-mode axis the dispatch ceiling gate (agentic-os#246) defines.

The deterministic parts (selection, ledger, dispatch, poll, outcomes) live in `scripts/backlog-loop.py`; the judgment (unblocking a stuck agent, the back-and-forth with the human) is the supervisor's, via the [tooling-backlog-loop](../.agents/skills/tooling-backlog-loop/SKILL.md) skill.

## What it reads, what it does not recompute

The loop reads the **tier** (`P0`-`P4`) and **mode** (`headless`/`interactive`/`consult`) labels `ward exec goose-triage` wrote. It does not re-triage. An unlabeled backlog is all `untriaged`, so `select` nudges when that lane is non-empty; `select --triage` folds `goose-triage` in first (whole scope) so the loop owns its inputs (agentic-os#278). Intra-tier order uses the latest cached triage score, else the issue number. All forgejo I/O routes through `ward ops forgejo` (ward-kdl) as the `coilyco-ops` bot, so the script holds no token. Dispatch shells `ward agent headless`.

## Lanes

- **headless** - the auto-burndown lane the loop dispatches. Narrow by design (fail-closed to `consult`).
- **interactive** - surfaced to the human to hand-drive, never auto-dispatched.
- **consult** / **untriaged** - held (human design call needed, or missing a label).

## Durable ledger

State persists at `~/.cache/agentic-os/backlog-loop/<owner>-<name>.yaml`, so the loop resumes after a restart. Per issue: `tier`, `mode`, `lane`, `score`, `state`, `container`, `dispatched_at`, `last_outcome`, `unblock_history`. States: `queued` -> `dispatched` -> `blocked`|`done`|`failed`; `surfaced` (interactive); `skipped` (consult/untriaged). A re-`select` refreshes metadata, never clobbering an in-flight state.

## Scope: many repos, one view

Drive more than one repo as a **scope** - `--repo a/b,c/d` makes `select` / `next` / `poll` aggregate one ranked view across the set (agentic-os#279). Per-issue verbs take a bare `<num>` or an `<owner/name>#<num>` ref. See [backlog-loop-scope.md](backlog-loop-scope.md).

## The outcome channel

A detached `ward agent headless` run has no host-side completion signal, nor an "I'm blocked" channel. The loop adds one: at dispatch it posts a protocol comment telling the agent to end with a comment whose first line is `WARD-OUTCOME: done` / `blocked - <the single decision or fact it needs>` / `failed - <why>`, candid retro below. `poll` reads that line - the agent reads issue comments into its seed, so v1 needs no ward change. Promoting it into the ward headless seed is a follow-up.

## A loop pass

```
ward exec backlog-loop -- select --repo coilyco-flight-deck/ward --triage  # triage + ledger + lanes
ward exec backlog-loop -- next --lane interactive                  # surface to human
ward exec backlog-loop -- dispatch 242                             # launch headless
ward exec backlog-loop -- poll                                     # reconcile
ward exec backlog-loop -- unblock 242 --note "use the staging DSN"  # re-queue
ward exec backlog-loop -- dispatch 242 --force                     # re-dispatch
```

Repeat poll -> unblock -> dispatch until the headless lane is `done`/`failed`, a handful at a time. An exited container with no outcome stays `dispatched`, flagged - read its log before retrying.

## See also

- [tooling-backlog-loop](../.agents/skills/tooling-backlog-loop/SKILL.md) - the supervisor skill.
- [goose-triage.md](goose-triage.md) - writes the tier + mode labels.
- [tooling-issue-prioritization](../.agents/skills/tooling-issue-prioritization/SKILL.md) - the tier/mode taxonomy.

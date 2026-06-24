# Repo-checkout tracker

A project-local status-line row that names the git checkouts on disk in `org/repo` form and flags the ones that have appeared since a baseline, so repos that quietly re-clone themselves back during dev work stop drifting onto disk unnoticed.

This repo dogfoods the [second status-line row](features-agents-sessions.md) hook with [`.agentic-os/statusline.sh`](../.agentic-os/statusline.sh). `scripts/agent-name.sh` runs that hook when present and appends its stdout as a second row under the agent name.

## What it shows

A single row, green when the on-disk set matches the baseline:

```
📦 15 repos
```

When checkouts have appeared since the baseline, it names them and colors the row (yellow for a little drift, orange once a lot has piled back on):

```
📦 15 repos  +2: coilysiren/website, coilyco-gaming/eco-app
```

The first few new names are listed; the rest collapse into `+N more`.

## How it scans

- Scan root is `~/projects` (override with `AOS_REPOS_ROOT`), where the org dirs live at `<root>/<org>/<repo>`.
- A `<root>/<org>/<repo>` counts as a checkout when `<repo>/.git` exists. `.git` is a directory for normal clones and a file for worktrees and submodules, so both are caught.
- The set is the sorted, de-duplicated list of `org/repo` names. The scan is a shallow stat over the org dirs, cheap enough to run on every status-line refresh.

## Baseline and re-anchoring

The baseline set persists across sessions under `~/.cache/agentic-os/repos/<key>.baseline`, one `org/repo` per line. The first run seeds it from whatever is on disk, so nothing reads as new until repos actually appear. New repos stay flagged until you re-anchor, which you do by deleting the baseline once you accept the current set:

```sh
rm -f ~/.cache/agentic-os/repos/*.baseline
```

The next refresh re-seeds the baseline from the current checkouts.

## Tunables

- `AOS_REPOS_ROOT` - directory holding the `<org>/<repo>` tree (default `~/projects`).

## Reuse in another repo

The hook is self-contained and reads no repo-specific state, so any repo can adopt it: copy `.agentic-os/statusline.sh` into the target repo (or symlink it), mark it executable, and `scripts/agent-name.sh` picks it up for sessions rooted there.

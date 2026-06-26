# Repo-checkout tracker

A project-local status-line row that names the git checkouts on disk that are **not** on an expected-repos list, i.e. the strays to remove. Repos quietly re-clone themselves back during dev work; this surfaces the ones that should not be there so they stop piling up.

This repo dogfoods the [second status-line row](features-agents-sessions.md) hook with [`.agentic-os/statusline.sh`](../.agentic-os/statusline.sh). `scripts/agent-name.sh` runs that hook when present and appends its stdout as a second row under the agent name. The same logic is baked into the [dev-base image](dev-base-image.md) as the `20-repos` provider of the [status-line composer](statusline.md) (a format-identical port - keep the two in lockstep), so a warded container shows this row too, and self-suppresses where there is nothing to scan.

## What it shows

When every checkout is on the expected list, a green all-clear with the count:

```
📦 15 repos, none stray
```

When checkouts are on disk that the list does not expect, it names them and colors the row (orange for a few, bold red once a lot have piled back on):

```
📦 7 to remove: coilyco-bridge/agentic-os-hardware, coilyco-bridge/deploy, coilyco-bridge/lore, coilyco-flight-deck/ward, +3 more
```

The first few stray names are listed; the rest collapse into `+N more`. With no expected list configured, the row degrades to just the count: `📦 15 repos`.

## The expected-repos list

A newline-delimited file of the repos that **should** be on disk, one per line, each `owner/name` or bare `name`. Lines starting with `#` and blanks are ignored. Resolution order:

1. `$AOS_REPOS_EXPECTED`, if set, points at the file.
2. Otherwise `~/.config/agentic-os/repos-on-disk.txt` (override the dir with `XDG_CONFIG_HOME`).

The hook stays generic and carries no repo names of its own. Point the conventional path at whatever manifest you treat as canonical, e.g. symlink it at your own list:

```sh
ln -sf /path/to/your/repos-on-disk.txt ~/.config/agentic-os/repos-on-disk.txt
```

## Fleet-org scope

Only checkouts under **your own orgs** are considered, so third-party upstreams (an external repo you cloned for reference) never read as strays. The fleet orgs come from a list of org names, one per line, resolved from `$AOS_FLEET_ORGS`, else `~/.config/agentic-os/fleet-orgs.txt`. A `<root>/<org>` whose `org` is not on that list is skipped entirely. With no fleet-orgs list, every org is in scope.

## How it scans

- Scan root is `~/projects` (override with `AOS_REPOS_ROOT`), where the org dirs live at `<root>/<org>/<repo>`.
- A `<root>/<org>/<repo>` counts as a checkout when `<repo>/.git` exists. `.git` is a directory for normal clones and a file for worktrees and submodules, so both are caught.
- Matching is by **repo name**: a checkout is expected when its `name` appears in the list (after dropping any `owner/` prefix from list entries), so the list may use either form. The scan is a shallow stat over the org dirs, cheap enough to run on every status-line refresh.

## Reuse in another repo

The hook is self-contained and reads no repo-specific state, so any repo can adopt it: copy `.agentic-os/statusline.sh` into the target repo (or symlink it), mark it executable, point `AOS_REPOS_EXPECTED` and `AOS_FLEET_ORGS` (or the conventional config paths) at your expected-repos and fleet-orgs lists, and `scripts/agent-name.sh` picks it up for sessions rooted there.

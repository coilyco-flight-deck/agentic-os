# Native agent workspaces

The shared shell shadows `claude`, `codex`, `goose`, and `opencode`. A supported
AOS binary first cleans recoverable predecessors and creates an isolated,
fleet-shaped workspace. No timer, daemon, exit hook, or operator command runs.

## Workspace projection

The expected-repositories file drives one linked worktree per checkout. Its
resolution uses `$AOS_REPOS_EXPECTED`, the conventional config path, then the
embedded baseline. Entries accept `owner/name` or bare names. The canonical
checkout supplies Git objects for a writable `aos/<harness>/<session-id>` branch.

A launch from `$PROJECTS_ROOT` enters:

```text
$TMPDIR/aos/native/<session-id>/projects/<owner>/<repo>
```

with the owner/repository hierarchy reproduced below `projects`. A repository
subdirectory maps to its session twin. An outside launch keeps its directory.
It still receives the full leased fleet workspace.

The shadow invokes agent-compose after projection, then execs the harness. Bare
harness commands let the native roster infer a role.
`acompose <role> <harness> [args...]` enters the clean shadow workspace for
non-directors. Director uses warded AOS because Ward owns dispatch and its
broker. Native AOS passes the harness model class and keeps role load points
outside repository worktrees. Its shadow home links host state but leaves user
skill directories empty. Claude auto-updates are disabled so a leased home
cannot replace the host launcher. Codex trusts only the generated workspace.
Assigned launches apply [bounded native Codex hook trust](native-codex-hook-trust.md).

## Startup leases

One JSON lease covers the session. It records process identity, source and
session directories, repositories, branches, and worktrees. Exec preserves the
PID through the vendor binary. The next launch detects a closed terminal.

Every launch cleans dead leases before creating its workspace. Live leases stay.
A clean dead worktree is removed only when its branch tip is reachable from
`origin`, then its local branch is deleted. Dirty, untracked, unpushed,
unreadable, and `*-workdir` state stays. Clean siblings may disappear alone.

## Ten-minute fleet pass

Every ten minutes at most, startup pulls expected repositories already on disk.
It fetches `origin`, then:

* A clean, inactive checkout on a remotely recoverable non-main branch switches
  to `main`, then deletes that local branch.
* A clean `main` fast-forwards to `origin/main`.
* An inactive linked worktree is removed with its local branch when clean and
  remotely recoverable.

It never creates merge commits, pushes, deletes remote branches, commits, or clones missing repositories.

## Unexpected clones

Fleet ownership comes from `$AOS_FLEET_ORGS` or its conventional config path.
A direct `$PROJECTS_ROOT/<owner>/<repo>` checkout is unexpected when its origin
belongs to a fleet org but the expected-repositories file omits it.

An unexpected clone must be inactive on clean `main` at fetched `origin/main`.
It cannot have linked worktrees, Git operations, submodules, ignored or
untracked files, or local-only branch, tag, stash, or reflog commits. Its origin
owner must match its directory owner.

The cache records an exact origin, HEAD, and branch fingerprint. The third
consecutive qualifying fleet pass deletes the clone. Any failed proof or
changed fingerprint resets its count. With the ten-minute pass interval, three
qualifying startups span at least twenty minutes.

## Local state

Leases and the pass cache use the platform cache at `agentic-os/native-shadow`.
AOS groups temporary state under platform `aos`: worktrees in `native`, requests
in `compose`, and bundles in `bundles`. `AOS_NATIVE_STATE_DIR` and
`AOS_NATIVE_SESSIONS_DIR` allow overrides. See the [shell owner](features-shell-secrets.md)
and [repo tracker](repo-tracker.md) for surrounding surfaces.

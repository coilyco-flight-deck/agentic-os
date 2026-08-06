# Native agent workspaces

The shared shell shadows `claude`, `codex`, `goose`, and `opencode`. A supported
AOS binary first cleans recoverable predecessors and creates an isolated,
fleet-shaped workspace. No timer, daemon, exit hook, or operator command runs.

## Workspace projection

Agent Compose's compiled residency plan drives one linked worktree per checkout.
AOS reads `$AOS_REPOSITORY_PLAN` or `~/.agent-compose/repository-plan.yaml`.
Legacy JSON remains a rollout fallback. No embedded roster exists. Exact
`owner/repository` identities supply writable worktrees from canonical Git objects.

A launch from `$PROJECTS_ROOT` enters:

```text
$TMPDIR/aos/native/<session-id>/projects/<owner>/<repo>
```

with the owner/repository hierarchy reproduced below `projects`. A repository
subdirectory maps to its session twin. An outside launch keeps its directory.
It still receives the full leased fleet workspace.

Native and standalone AOS use this shadow before agent-compose or Docker runs.
Bare harness commands let the native roster infer a role.
`acompose <role> <harness> [args...]` enters the clean shadow workspace for
non-directors. Director uses warded AOS because Ward owns dispatch and its
broker. Native AOS clears deprecated Agent Compose model selectors, so every
harness receives the complete selected role composition. User skills stay empty.
Claude auto-updates cannot replace the host launcher, and Codex trusts the workspace.
Assigned launches apply [bounded native Codex hook trust](native-codex-hook-trust.md).

## Startup leases

One JSON lease records process identity, directories, repositories, branches,
and worktrees. Exec preserves the PID through the vendor binary, and the next
launch detects a closed terminal. Resolved identity keeps path aliases leased.

Every launch timestamps a dead lease and preserves its worktrees for 24 hours.
After the grace, AOS removes a clean worktree only when its branch tip is reachable
from `origin`, then deletes its local branch. Dirty, untracked, unpushed, unreadable,
and `*-workdir` state stays. Clean siblings may disappear alone after the grace.

## Ten-minute fleet pass

Every ten minutes at most, startup pulls resident repositories already on disk.
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
belongs to a fleet org but compiled residency omits its exact identity.

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

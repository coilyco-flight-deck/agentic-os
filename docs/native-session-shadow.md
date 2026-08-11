# Native session shadow

A native AOS launch runs the agent inside a per-session shadow instead of the
canonical checkout. This page holds the mechanics behind the AGENTS.md rules
that reference it. Workspace projection itself is in
[native agent workspaces](native-agent-workspaces.md).

## Session markers

`AOS_NATIVE_SESSION` carries the session id and `AOS_NATIVE_SESSION_PROJECTS`
carries the session `projects` root. Both are exported only by a launch that
links at least one worktree. A launch linking none leaves both unset, because it
stays in the canonical checkout and no isolation claim would be true there. An
agent reads the pair as the authoritative answer to whether it is isolated,
rather than pattern-matching its own working directory against a path.

`AOS_REPO_ROOT` names the canonical checkout and is unrelated. It is set by the
shell base and the container entrypoint, so it stays populated inside a shadow
and points away from it.

## Durability asymmetry

Session worktrees are linked from the canonical repository, so they share its
Git object store. A commit is durable the moment it is written, because the
objects land in the canonical repository rather than in the session directory.
Branch refs likewise outlive the session.

The working tree has no such protection. It lives under the platform temporary
root, which the operating system purges on its own schedule. macOS empties
`DARWIN_USER_TEMP_DIR` through `com.apple.bsd.dirhelper`, deleting files by
access time and leaving the directory skeleton behind, which surfaces in Git as
a worktree that is `prunable` with a missing gitdir.

Committed work therefore survives a purged shadow and uncommitted work has no
second copy. That asymmetry is the mechanism behind the remote-checkpoint rule,
which is why the rule is stated as a consequence rather than an edict.

## Hand-made worktrees

An agent working without a shadow still needs isolation from a checkout holding
foreign work. Those worktrees belong under the platform cache at
`agentic-os/agent-worktrees`, not in the temporary directory. A hand-made
worktree carries no session lease, so nothing sweeps or recreates it, and a
purge there destroys the only copy of anything uncommitted.

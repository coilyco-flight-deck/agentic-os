# Native default branch ownership

Why the canonical checkout owns `main`, and the three guards that keep it that
way. Companion to [native agent workspaces](native-agent-workspaces.md).

## A worktree on main takes it from everyone

Git allows one checkout of a branch per repository, so a linked worktree
holding `main` takes it from the canonical checkout, which then cannot switch
back. The fleet pass that would have returned it fails the same way rather than
repairing it, so the checkout stays parked on a stale branch indefinitely.

Squatting is worse than a lock, because branch configuration is
repository-global. A worktree sitting on `main` that pushes with an
upstream-setting push rewrites `branch.main.merge` for every worktree including
the operator's. With `pull.rebase` set, their next `git pull` rebases `main`
onto a session branch and reports divergence against a ref nobody chose. That
failure is silent and reads like their own commits went wrong.

Startup therefore detaches any non-canonical worktree found on `main`, at the
same commit so the working tree is untouched, and resets `branch.main.merge`
when it points elsewhere. Both are backstops. An agent stays on its session
branch and uses a detached HEAD when it needs main's content.

## Absence is not uncertainty

The live-worktree set fails closed: when a path cannot be identified, every path
reads as live and the pass does nothing. A purged temporary root used to trip
that, because a lease naming a worktree that no longer exists made
`EvalSymlinks` fail. One purged session disabled the whole pass indefinitely.

Absence now answers "not live". Only a path unreadable for another reason still
fails closed.

## Branch reaping

The pass deletes a local branch when `rev-list <branch> --not --remotes=origin`
is empty, so every commit on it already exists on the remote. That is stricter
than `git branch --merged`, which would delete a branch whose commits reached
main but were never pushed anywhere.

Checked-out branches, worktree-held branches, and the `aos/` namespace are
skipped. `aos/` is session bookkeeping released by the lease path, and
session-ID uniqueness reads it to tell whether an ID is taken, so reaping it
would hand out an ID another session still owns.

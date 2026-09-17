---
name: tooling-workspace-isolation
description: Where an agent may work in a native checkout - session shadows, foreign work, unlisted clones, serialized repos, and directories reserved for Kai. Load before the first mutation in a checkout the agent doesn't already know it owns. Triggers - native session shadow, AOS_NATIVE_SESSION, foreign checkout, worktree, unlisted clone, serialized checkout, -workdir.
---

# Workspace isolation

Extracted from the always-loaded base so these situational checkout rules stop
sitting on every session's context floor. Load before the first mutation
whenever ownership of the current checkout is not already established.

## Native session shadow

A native AOS launch runs the agent in a per-session shadow, not the canonical
checkout. `AOS_NATIVE_SESSION` and `AOS_NATIVE_SESSION_PROJECTS` are set
exactly when it exists, so the agent reads them rather than guessing. The
shadow shares canonical Git objects, so a commit is durable at once while its
working tree stays exposed to temporary-root purges, the mechanism behind the
rule below. Placement and mechanics:
[session shadow](../../../docs/native-shadow.md).

**Never leave a shadow worktree on the default branch.** Git allows one
checkout of a branch per repository, so a shadow that finishes by switching to
`main` takes it from the canonical checkout, which then sits stale until
someone tries to switch back. Ending a task by merging, switching to `main`,
and deleting the branch is correct hygiene in an ordinary clone and takes the
fleet's default branch hostage here. Stay on the session branch, and detach at
a commit when you need main's content. Startup detaches a squatter, as a
backstop rather than a licence:
[default branch ownership](../../../docs/native-session-start.md).

## Foreign work requires a worktree

This rule governs a session with no native shadow. Before the first mutation
in any native checkout, the agent inspects the worktree, current branch, and
local divergence. If the checkout contains work the agent did not create for
the current task, the agent **must not edit, format, stage, stash, reset,
switch branches, commit, or otherwise mutate that checkout**. The agent
instead takes a task-specific branch and linked worktree from a clean
canonical base, leaves the original checkout exactly as found, and never
absorbs foreign changes or substitutes stash for isolation. Pre-existing
staged, unstaged, or untracked files, local commits, an in-progress Git
operation, and a branch owned by another task all count as foreign, as does
ambiguous ownership. If the agent cannot create that worktree safely, it stops
before any mutation and reports the exact blocker.

## Unlisted repository clones stay temporary

Before cloning a repository, the agent checks the host's
expected-repositories list when that surface is configured. If the repository
is not explicitly listed as one that belongs on disk, the agent clones it
into the resolved temporary directory with a task-specific basename, never
under the persistent projects or workspace tree, treats that clone as
task-scoped, and removes it once the work is complete and remote-checkpoint
requirements are satisfied. An absent or unreadable list does not authorize a
persistent checkout.

## A foreign checkout is somewhere to read, not somewhere to run from

The rule above bounds what an agent may **write** in a checkout it does not
own, and says nothing about what it may **run** from inside one. A privileged
command resolves against its working directory: `python3 -m` prepends that
directory to `sys.path`, so a module import inside a foreign clone loads the
clone's code first, in a process that may already hold a decrypted
credential, and `PYTHONPATH` does not save it because the working directory
wins. The same shape reaches anything resolving configuration, plugins, or
hooks by name. So **invoke an operator verb, a credential-bearing command, or
anything resolving a module or plugin by name from a directory the estate
authored**, leaving the foreign checkout first. Reading its files, running git
against it, and inspecting it are untouched, because the rule is about
execution carrying authority rather than about presence. **The trigger is
ordinary rather than adversarial**, so nothing about it looks wrong from
inside the session, and a guard validating argv cannot see it either because
the substitution happens at import. Where tooling can enforce the safe form it
should, and this rule covers every case it does not reach.

## Serialized checkouts invert isolation

A repository in the serialized set inverts the three rules above. The agent
works it in the canonical checkout under `$PROJECTS_ROOT`, never in a shadow,
a worktree, or a temporary clone, and treats it as belonging on disk whether
or not residency lists it. The named set, the one-writer reason, and what to
confirm first:
[native agent workspaces](../../../docs/native-agent-workspaces.md).

## Human-only workdirs

A checkout whose directory basename ends in `-workdir` is reserved for Kai's
manual work. Agents treat it as outside the workspace: agents do not inspect,
enter, edit, validate, format, stage, stash, or include it in fleet or
recursive tooling. If an agent launches inside one, the agent stops before
inspecting repository contents and moves to the canonical checkout or an
agent-owned linked worktree.

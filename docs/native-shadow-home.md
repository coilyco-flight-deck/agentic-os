# Native shadow home

An assigned-role launch stages a shadow `HOME` under the session root. Every
host entry becomes a symlink back to the real home, so credentials, caches, and
tool config keep working. `.agents` and `.claude` are filtered rather than
linked whole, and their `skills` directories stay empty for the composed role.

## The projects hole

`$PROJECTS_ROOT` is the one host entry the shadow home leaves out.

The session already owns writable worktrees under `<session>/projects`, one per
resident checkout, each on its own `aos/<harness>/<id>` branch. Linking the host
projects root into the shadow home would give the canonical checkouts a second
name inside the session. That name resolves past the worktrees to the shared
trees on `main`, and it looks exactly as natural as the real one.

An agent that reaches for `~/projects/<owner>/<repo>` out of habit lands in the
shared checkout, edits it, and commits there. Two sessions doing that at once
collide over one index, and each can absorb the other's in-flight files into its
commit. Both stay entirely inside their own isolation the whole time.

Leaving the entry absent turns that into an immediate "no such file or
directory" instead of a silent wrong answer. The failure names itself at the
first command rather than at the first collision.

## Working in a session

Use the launch directory and relative paths. `pwd` at startup is the session
tree, and `git rev-parse --git-dir` resolves to a `worktrees/` entry under the
canonical repository, which is how a session checkout is recognized.

Reaching the canonical tree on purpose is still possible through its absolute
`/Users/<user>/projects` path. That is deliberate: the guard removes the
accident, not the capability, and the explicit path reads as a decision in a
transcript.

## Scope

The rule binds `stageNativeRoleHome`, which serves assigned-role and workspace
-root launches. `stageStandaloneRoleHome` copies a narrow allowlist instead of
mirroring the home, so it never had the entry. A `PROJECTS_ROOT` override is
matched by inode identity, not by the literal name `projects`.

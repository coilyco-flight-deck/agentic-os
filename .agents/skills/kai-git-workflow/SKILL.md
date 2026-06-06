---
name: kai-git-workflow
description: Git workflow for coilysiren/* - base rules, coily/infrastructure exceptions, readonly SSH, Forgejo as default tracker, flaky-test discipline. Triggers - git workflow, commit, push, PR, gh, issue tracker, coily, lockdown, file a todo, forgejo, flaky test, flake.
---

# Git workflow

Default across `~/projects/coilysiren/*`:

- Commit to `main` directly; push after each. No PRs unless asked.
- Run tests, linters, builds without asking. Fix failures.
- Never `--no-verify`.
- Readonly git/shell auto-allowed.
- Every commit closes a same-repo issue. File first, then commit with `closes #N` / `fixes #N` / `resolves #N`.
- `agentic-os-kai` only: one commit per discrete additive change.
- `git commit --amend` is fine pre-push, preferred over a "fix lint" follow-on for hook fixes. If the amend changes substance relative to the closing-issue description, post a comment on that issue so the audit trail survives. Force-push off-limits. Overrides the default Claude Code rule.

Never run destructive git commands unless Kai explicitly asks. Never revert changes you didn't make.

Below are the exceptions and details.

## Recovering a commit dropped by rebase

`coily git pull --rebase` can silently drop a local commit when upstream `main` was force-pushed (release-please rewriting history). Git's default `--fork-point` heuristic reads the upstream reflog, decides the local commit is "already upstream," and drops it - no error, no conflict, just gone from `HEAD` and the working tree. The wrapper does **not** guard against this by design: it stays thin and security-focused, and the commit is only dangling, never lost. Recover it from reflog:

```
git reflog                 # find the pre-rebase HEAD (the entry just before "rebase ...")
git cherry-pick <sha>      # replay the dropped commit onto the rebased HEAD
```

Use `git reset --hard <sha>` instead of cherry-pick only when nothing else has moved since. Decided in coily#4 (no default-behavior change, reflog is the documented solve).

## Repo-specific exceptions

- **coily** - auto-push only when session's primary cwd is coily. Not if started in a sibling and cd'd in. Check env block, not live cwd.
- **infrastructure** - auto-commit/push code/CI. Confirm before SSM/kubectl/cloud writes. Never print decrypted SSM values. Reach for `coily` before raw aws/kubectl.
- **message-ops** - confirm before destructive social ops (archive, delete, block). Friends-list check before any archive pass.

## Readonly SSH

Bare ssh to kai-server is readonly. Cluster reads run via `sudo k3s kubectl` (host-side NOPASSWD sudoers, scoped to that exact path). Writes need explicit confirmation, typically via `coily` or CI.

## Deploy knowledge

`~/projects/coilysiren/infrastructure/docs/k3s-deploy-notes.md` is source of truth for k3s topology, SSM layout, GH Actions → cluster deploys, manifest shapes, triage. Deployable repos reference it.

## Pre-commit canonical entry

Every repo has `.pre-commit-config.yaml` with offline trufflehog:

```yaml
- id: trufflehog
  name: trufflehog (secret scan, offline)
  entry: trufflehog git file://. --since-commit HEAD --no-verification --no-update --fail
  language: system
  pass_filenames: false
  stages: [pre-commit, pre-push]
```

## More detail

- [GitHub issues as work tracker](references/github-issue-tracker.md) - precedence, close-via-commit, tracker issues stay open, bot-attribution signature.
- [Privileged ops via coily](references/coily-privileged-ops.md) - read vs write surface, thin pass-throughs, disabling PRs via GraphQL.
- [Default TODO destination and flake discipline](references/default-todo-and-flake.md) - Forgejo as default tracker, never-ask-just-file, flaky-test rule.

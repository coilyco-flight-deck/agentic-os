---
name: coding-gish
description: The "issue commit push" landing sequence as a single command. File a same-repo GitHub issue, commit with `closes #N`, push. Optimized for mobile dictation where true slash commands don't work. Triggers - gish, /gish, issue commit push, file issue and commit, file issue and push, land this change, ship this change, close this out, gi-sh.
---

# coding-gish

One-word handle for the canonical change-landing sequence in any `coilysiren/*` repo: **gi**thub issue, commit, pu**sh**.

## When this fires

Kai dictates "gish" (or any trigger from the description). The current working tree has staged or unstaged changes that need to land on `main`.

## Procedure

1. **Survey the change.** `git status` + `git diff` to understand what's about to land. Stay terse on mobile output.
2. **File a same-repo GitHub issue.** Title and body describe the change in the same shape the commit message will use. Use `coily ops gh issue create --repo <owner>/<repo> --body-file /tmp/<slug>.md` (never `--body` with a heredoc - the coily policy gate rejects shell metacharacters).
3. **Stage and commit.** Add the relevant paths by name (never `git add -A`, never `git add .` per AGENTS.md). Commit message ends with `closes #N` where N is the issue from step 2. Never `--no-verify`.
4. **Push.** Straight to `main`. If the push is rejected for non-fast-forward, `git pull --rebase origin main` and push again. Never force-push.
5. **Report.** One line: issue link, commit hash, push result.

## Hard rules

- The issue must be in the **same repo** as the commit. Same-repo `closes #N` is what the `closes-issue` pre-commit hook enforces; a cross-repo reference is rejected.
- Never skip step 2. The hook will block you anyway.
- Never run destructive git operations (reset --hard, push --force, branch -D) inside this flow.
- If the commit fails on a pre-commit hook, fix the issue and `git commit --amend` rather than stacking a "fix lint" follow-on commit. Amend is preferred for linter / hook fixes per AGENTS.md (unpushed commits only; force-push is still off-limits). If the amend materially changes the diff relative to what the closing issue described, leave a comment on the GH issue noting the amendment.

## Cross-links

- [`kai-git-workflow`](../../../../agentic-os-kai/.agents/skills/kai-git-workflow/SKILL.md) - the same-repo issue rule, readonly exceptions, lockdown notes.
- [`coding-github`](../coding-github/SKILL.md) - the broader GitHub umbrella, including the GraphQL hard rule.
- [`coily-ops-gh-meta`](../../../../agentic-os-kai/.agents/skills/coily-ops-gh-meta/SKILL.md) - `coily ops gh` passthrough semantics, including the `--body-file` workaround for the shell-metacharacter gate.

**Why this is one skill not three:** the three steps fail open if you skip one. An issue without a commit is a dangling intent. A commit without an issue gets rejected by the hook. A commit without a push is invisible. Bundling enforces all three.

agentic-os#84 - origin.

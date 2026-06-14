---
name: kai-gish
description: Kai's land-flow shorthands. `gish` lands one repo's current working tree (issue + commit minus lockdown files + push to Forgejo main). `gulp` drains everything else that could be lost (stashes, all branches, all worktrees) across every coily*/* repo - see references/gulp.md. Triggers - gish, land this, gulp, gulp every coily repo.
---

# gish - one-word land flow

`gish` is Kai's analog to a Warp alias: she says the single word `gish` (or `gish: <hint>`) in chat and Claude runs the whole land sequence so she never spells out "make an issue, commit, push." Claude does the judgment (issue text, commit message, new-vs-existing); Kai just says the word. It is an **in-chat shorthand**, not a binary.

For the heavier cross-repo "drain everything" sweep, see **`gulp`** below.

## What "gish" means

Run these in order, in the repo at cwd's git toplevel. Route git/forgejo calls through the repo's normal guard (`coily ops forgejo` for issues; bare `git` where no verb exists - this repo's `ward` is the cli-guard, not a git passthrough).

1. **Read the work.** `git status --short` + `git diff` (and untracked). Clean tree -> stop, nothing to land.
2. **Resolve the repo.** `owner/name` from the forgejo remote (`git remote -v`; `origin` is usually forgejo directly). Issue base `https://forgejo.coilysiren.me/<owner>/<repo>`.
3. **Find or create the issue.** Reuse an open issue that clearly matches the diff/`<hint>`, else create one Claude writes from the diff: `coily ops forgejo issue create --repo <owner/name> --title <t> --body-file <tmp.md>`. Capture the issue **number**; build `ISSUE_URL=<base>/issues/<N>`.
4. **Commit dirty, minus lockdown files.** From `git status --porcelain` **drop** `.claude/settings.json` and `.claude/lockdown-deny.sh` (doctrine forbids staging them; the harness hard-blocks the former). Then `git commit -m "<type>(<scope>): <subject>" -m "closes <ISSUE_URL>" -- <paths...>`. Naming paths stages+commits atomically; untracked files land by being named.
5. **Push to canonical main.** `git push "$(git config --get-all remote.origin.pushurl | grep forgejo)" HEAD:main` (or `git push forgejo HEAD:main` with a named remote). Forgejo only, never the PR-gated GitHub mirror.
6. **Report in one line:** issue (reused/created #N) + commit subject + push landed.

## Rules baked in

- **Never stage the lockdown files.** Excluded from the path list every time; leave them dirty, do not stash around them.
- **Issue before commit.** The body carries `closes <ISSUE_URL>`, so the issue exists first. Same-repo issue only.
- **FEATURES.md.** If the change adds/removes/reshapes a feature, update that repo's `docs/FEATURES.md` in the same commit.
- **Never `--no-verify`.** If a hook fails, surface it and fix the cause - do not bypass.
- **`<hint>` is optional steering.** `gish: bump retry backoff` seeds title + subject; with no hint, derive from the diff.

## When to confirm vs just run

`gish` is pre-authorized (commit + push to Kai's own canonical main is her normal flow). Just run it. Pause only if: the tree spans two unrelated features (offer to split), a hook fails, or the diff touches something destructive Kai likely didn't mean to land.

# gulp - drain everything, everywhere

`gulp` is the heavy sweep: capture **every change that could be lost** (working tree, stashes, all branches, all worktrees) and land it on canonical, across **every coily repo at once**. Bare `gulp` fans out over every git repo under `~/projects/coily*/*`. `gulp this repo` narrows to cwd. An in-chat shorthand, not a binary.

**Read [`references/gulp.md`](references/gulp.md) before executing.** Invariants: ff-only sync first (never merge/rebase), the `coily*` glob covers `coilysiren/`, GitHub-only profile repos (`.github`, `coilysiren/coilysiren`) land to GitHub not Forgejo and are never skipped for a missing Forgejo remote, branches via `push --all` (never force-merged), stashes never dropped, never `--force` or `--no-verify`.

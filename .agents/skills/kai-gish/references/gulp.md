# gulp - drain everything, everywhere

Full mechanics for `gulp`. See [`../SKILL.md`](../SKILL.md) for `gish`, the one-repo land this builds on.

`gish` lands only the current working tree. `gulp` adds the three classes `gish` leaves behind - **stashes, other branches, other worktrees** - and drains every repo across the fleet.

## Scope

- **Bare `gulp`** (or `gulp every coily repo`) - every git repo under `~/projects/coily*/*`. Enumerate `~/projects/coily*/` at run time. **Never hardcode the org list, never narrow to `coilyco-*`** - `coilysiren/` is Kai's personal org and is in scope every time (it holds the GitHub-only profile repo, below). Skip the org dirs themselves and any non-git subdir.
- **`gulp this repo`** - the git toplevel at cwd only.

## Per repo

Resolve `owner/name` + one `ISSUE_URL` once (gish steps 2-3), reused across all of this repo's land commits. Then:

0. **Fast-forward first** - `git pull --ff-only` from the canonical remote so local main absorbs what's there. `--ff-only` is deliberate: never a merge, rebase, or invented history. A repo that cannot ff is not an error - **dirty** falls to step 1, **no-upstream / detached** skips with a report, **diverged** skips as "needs manual merge."
1. **Working tree** - `gish` steps 1-5 (issue, commit tracked+untracked minus the lockdown files, push `HEAD:main`). A clean tree is fine.
2. **Stashes** - per `git stash list`, oldest first: `git stash apply`, commit closing the same issue, push. **Never drop a stash** - leave every `stash@{n}` as a backup. On apply conflict: reset clean (`git checkout -- .`), leave it, report "needs manual merge."
3. **All branches - merge, delete, keep the rest.** With main ff'd to canonical (step 0), merge each local branch (other than main) into main. **Clean or already-merged:** keep it, then `git branch -d <branch>` so it never needs re-checking. Push main once after. **Conflict:** `git merge --abort`, leave the branch, push it to canonical as its own branch, flag "needs manual merge." Always `-d` never `-D`, so git refuses to delete an unmerged branch. Never force-merge or force-delete.
4. **Other worktrees** - `git worktree list`; in each one besides the drained one, repeat **step 1 only** (its tree lands onto its own branch). Stashes and branches are repo-global, already done.

## Canonical remote - Forgejo, GitHub-only as the exception

`<canonical>` is the Forgejo pushurl (`git config --get-all remote.origin.pushurl | grep forgejo`) for nearly every repo. A rare class has **no Forgejo canonical** - GitHub is the source of truth, because they back a GitHub-only feature:

- **Org-profile `.github` repos** - render an org's public profile README. `coilyco-flight-deck/.github` is on disk as `dotgithub`.
- **Personal-profile repo** - `coilysiren/coilysiren`.

Resolve as **"the live Forgejo pushurl if one exists, else the GitHub `origin`"**. If the grep is empty or the Forgejo push 404s, land steps 1 and 3 to GitHub `origin`. **Never skip a repo for an empty grep** - empty means "land to GitHub," not "undrainable." A 404ing `.github.git` remote is mis-wired, not a reason to park - drain to GitHub and flag the stale remote.

## Report

One block per repo, then a roll-up. Per repo: ff'd / up-to-date / couldn't-ff (with reason), issue #N, commit subjects, stashes landed / skipped, branches merged+deleted / kept, worktrees swept. **Flag every "needs manual merge" stash, every conflicting branch kept, and every couldn't-ff repo** so nothing silently stays behind.

## Confirm vs run

`gulp` is pre-authorized - it only pushes to Kai's own canonical mains (Forgejo, or GitHub for the profile repos) - so run it across many repos without a permission loop. **Surface, never force, when:** a stash apply conflicts, a branch cannot push non-destructively, a hook fails (fix the cause, never `--no-verify`), or a diff looks like work Kai clearly did not mean to land. Conflicting branches go up as their own branch, never force-merged onto main.

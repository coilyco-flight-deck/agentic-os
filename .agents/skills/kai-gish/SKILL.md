---
name: kai-gish
description: Kai's one-word land flow. On "gish" (+ optional hint), find/create a Forgejo issue, commit all dirty work (minus lockdown files) closing it, push to Forgejo main. Triggers - gish, land this.
---

# gish - one-word land flow

`gish` is Kai's analog to a Warp alias: she says the single word `gish` (or `gish: <hint>`) in chat and Claude executes the whole land sequence so she never has to spell out "make an issue, commit, merge, push." Claude does the judgment (issue text, commit message, new-vs-existing); Kai just says the word.

This is an **in-chat shorthand**, not a binary. There is no `gish` on `PATH`. When Kai types `gish` to a non-Claude shell it will error - that is expected, the word is for Claude.

## What "gish" means

Run these steps in order, in the repo at the current working directory's git toplevel. Each git/forgejo call routes through coily.

1. **Read the work.** `coily git status` (short) + `coily git diff` (and untracked). If the tree is clean, stop and say so - nothing to land.
2. **Resolve the repo.** `owner/name` from the forgejo remote: `git remote get-url forgejo` (or parse `origin`'s forgejo pushurl). Issue URL base is `https://forgejo.coilysiren.me/<owner>/<repo>`.
3. **Find or create the issue.** `coily ops forgejo issue list --repo <owner/name>`. If an open issue clearly matches the diff (and/or Kai's `<hint>`), reuse it. Otherwise create one whose title + body Claude writes from the diff: `coily ops forgejo issue create --repo <owner/name> --title <t> --body-file <tmp.md>`. Capture the new issue **number** from the output (fall back to `issue list` if the create output is terse). Build `ISSUE_URL=<base>/issues/<N>`.
4. **Commit everything dirty, minus the lockdown files.** Gather the path list from `git status --porcelain` and **drop** `.claude/settings.json` and `.claude/lockdown-deny.sh` - doctrine forbids staging them, and the harness hard-blocks committing `.claude/settings.json`. Then:
   `coily git commit -m "<type>(<scope>): <subject>" -m "closes <ISSUE_URL>" -- <path1> <path2> ...`
   Naming the paths stages + commits them atomically (coily#7); untracked files land by being named. Message is conventional-commits 1.0.0 with a `closes <ISSUE_URL>` body - gish's own house style for a clean landed history, not a hook requirement (the `conventional-commit` + `closes-issue` hooks ship off by default now).
5. **Push to canonical main.** `coily git push "$(git config --get-all remote.origin.pushurl | grep forgejo)" HEAD:main` (equivalently `coily git push forgejo HEAD:main` when a named `forgejo` remote exists). Push to **forgejo only**, never the PR-gated GitHub mirror.
6. **Report in one line:** issue (reused #N or created #N) + commit subject + that the push landed.

## Rules baked in

- **Never stage the lockdown files.** `.claude/settings.json` and `.claude/lockdown-deny.sh` are excluded from the path list every time. Leave them dirty in the tree; do not stash around them.
- **Issue before commit.** The commit body must carry `closes <ISSUE_URL>`, so the issue has to exist first. Same-repo issue only.
- **FEATURES.md.** If the change adds/removes/reshapes a feature, update that repo's `docs/FEATURES.md` in the same commit (include it in the path list) per the trifecta rule.
- **Never `--no-verify`.** If a pre-commit or commit-msg hook fails, surface it and fix the cause - do not bypass.
- **`<hint>` is optional steering.** `gish: bump retry backoff` seeds the issue title + commit subject; with no hint, derive both from the diff.

## When to confirm vs just run

`gish` is pre-authorized for the land sequence above (commit + push to Kai's own canonical main is her normal flow). Just run it. Pause only if: the tree spans changes that look like two unrelated features (offer to split), a hook fails, or the diff touches something destructive/out-of-scope Kai likely didn't mean to land.

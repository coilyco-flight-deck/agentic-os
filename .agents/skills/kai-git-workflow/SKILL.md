---
name: kai-git-workflow
description: Git workflow exceptions for coilysiren/* - coily/infrastructure rules, readonly SSH, issues as tracker. Triggers - git workflow, commit, push, PR, gh, issue tracker, coily, lockdown.
---

# Git workflow exceptions

Default rules (commit-to-main, push-after-each, no PRs, run-checks, never `--no-verify`, pre-commit with offline trufflehog) live in `AGENTS.md`. Below are the exceptions and details.

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

# GitHub issues as work tracker

When a coilysiren repo has an active issue tracker, issues are canonical - not vault inbox, not TodoWrite, not memory.

- **Open issues for new requests** before starting. Enough detail to act cold, labels matching the repo's scheme, cross-links. **Don't ask first.** When a change in a repo with an active issue tracker needs a closing issue, file it and proceed. The answer is always yes. Only ask if the issue's framing is genuinely ambiguous (scope unclear, multiple plausible repos), not just to confirm filing it.
- **Close via commit subject** - `fixes #N` / `closes #N` auto-closes on push. For partial/tangential work, use `refs #N` and close manually: `gh issue close N --comment "<sha>: <one-liner>"`.
- **Tracker issues stay open.** When a commit's work is motivated by a long-lived tracker (a collector issue meant to accumulate cases, drifts, or TODOs over time), do not `closes` the tracker. File a *separate atomic issue* for the commit and `closes` that one. Cheaper than rewriting the commit-msg hook to support non-closing keywords. Confirmed 2026-05-14: a Wispr Flow dictionary tracker got auto-closed by a commit that should have closed its own atomic implementation issue. Reopening works but pollutes the issue's state history.
- **Skip for trivia** - typos, formatting sweeps, one-liners. No issue tracker → don't manufacture one.

## Bot-attribution signature

Claude-filed issues (and Claude-written issue comments) are wrapped top and bottom with `> 🤖 Filed by Claude Code on Kai's behalf.` as a blockquote. Top line, blank line, body, blank line, bottom line. Same convention as the `Co-Authored-By` trailer on commits - makes attribution scannable without a separate bot account. Skip for Kai-authored content she's just asking Claude to post verbatim.

Check `gh issue list --repo coilysiren/<name>` when unsure.

## Privileged ops via coily

Reach for `coily gh ...`, `coily ops aws ...`, `coily kubectl ...`, `coily ssh kai-server` etc. for privileged ops. Bare invocations of the *write* surface are denied by lockdown - destructive verbs (gh pr create/edit/merge, aws s3 cp, kubectl apply/delete, etc.) only work through coily, which gates them on argv validation and writes the audit row.

**Read verbs are explicitly allowed bare** (`aws s3 ls`, `gh pr view`, `kubectl get pods`, etc.) - lockdown's allow list enumerates them, and bare reads are fine to use directly when convenient. The "everything through coily" rule that used to live here was always a hygiene preference rather than a security boundary, and it was stricter than what lockdown actually enforces.

`coily gh` / `coily ops aws` / `coily kubectl` are now thin pass-throughs (issue #27) - they take the same args as the underlying CLI verbatim, no flag parsing on coily's side. **Limitations:** coily rejects shell metacharacters in argv (no `|`, `&`, `>` inside an argument), so pipe / redirect *outside* the coily call (`coily gh ... > /tmp/x.json`) is fine but keep them out of any single arg.

## Disabling pull requests on a repo

GitHub's per-repo "disable pull requests" toggle (shipped Feb 2026) must be set via **GraphQL**, not REST. This is a sanctioned exception to the REST-default rule: the REST path is broken. `has_pull_requests` on `PATCH /repos/{owner}/{repo}` echoes whatever you send but does not persist, and the REST `GET` reads back stale/inverted values - do not trust it to confirm state. GraphQL `Repository.hasPullRequestsEnabled` is authoritative both to read and to write.

```graphql
# resolve the repo node id (and read current state)
query { repository(owner:"coilysiren",name:"REPO"){ id hasPullRequestsEnabled } }
# disable PRs
mutation { updateRepository(input:{repositoryId:"R_...",hasPullRequestsEnabled:false}){ repository{ name hasPullRequestsEnabled } } }
```

`pullRequestCreationPolicy` (`ALL` / `COLLABORATORS_ONLY`) is the softer "who can open PRs" dropdown, also on `updateRepository`. Pass the query as a file - `coily ops gh api graphql -F query=@/tmp/q.graphql` - because coily's metacharacter gate rejects the `{ }` in an inline `-f query=...` arg. Origin: coilysiren/agentic-os-kai#676.

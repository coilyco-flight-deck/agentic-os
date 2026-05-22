---
name: coding-github
description: GitHub umbrella skill. Carries the GraphQL hard rule (never reach for gh api graphql without double-confirming, REST is default), and routes to PR-lifecycle and coily-passthrough siblings. Triggers - github, gh, gh cli, gh api, octokit, graphql, repo, repository, pull request, PR, issue, fork, branch, workflow, action, release, tag, label.
---

# coding-github

Umbrella skill for any work that touches GitHub. Owns the broad keyword surface, carries the hard rules that apply to every GitHub touch, and routes to the focused siblings for specific lifecycles.

## Hard rule: never use the GitHub GraphQL API without confirming first

Never reach for the GitHub GraphQL API (`gh api graphql`, `octokit.graphql`, raw POSTs to `/graphql`, etc.) without double-confirming with Kai first. State that the proposed approach uses GraphQL, name a REST alternative if one exists, and wait for an explicit go-ahead before running or writing the call.

Applies to one-off commands, scripts, workflows, skills, and any code Kai will run.

**Why:** GraphQL rate limits have burned three days of Kai's time. The recovery is slow and annoying, and the burn is silent until limits hit.

**How to apply:** default to REST (`gh api /repos/...`, search endpoints, list endpoints) and accept the extra round-trips. REST rate limits are far more forgiving and the failure mode is per-call, not per-account.

## Routing

- **PR lifecycle** (create branch, commit, open PR, monitor CI, auto-fix failures, merge) - [`coding-github-pr-workflow`](../coding-github-pr-workflow/SKILL.md).
- **Coily passthrough for `gh`** (audit-log binding, scope routing) - [`coily-ops-gh-meta`](../coily-ops-gh-meta/SKILL.md).
- **Git workflow for `coilysiren/*` repos** (commit-to-main default, every-commit-closes-an-issue rule, readonly exceptions) - [`kai-git-workflow`](../kai-git-workflow/SKILL.md).
- **Autonomous engineering across the backlog** - [`kai-autonomous-engineering`](../kai-autonomous-engineering/SKILL.md).

## See also

- [AGENTS.md "GitHub Issues - Echo on Touch"](../../../AGENTS.md) - quoting rules for `owner/repo#N` refs and issue URLs.
- agentic-os-kai#561 - this skill's origin.

---
name: coding-github-pr-workflow
description: Full pull request lifecycle - create branches, commit changes, open PRs, monitor CI status, auto-fix failures, and merge. Works with gh CLI or falls back to git + GitHub REST API via curl.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review]
---

# GitHub Pull Request Workflow

Complete guide for managing the PR lifecycle. Each step shows the `gh` way first, then the `git` + `curl` fallback for machines without `gh`.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository with a GitHub remote

### Quick Auth Detection

```bash
# Determine which method to use throughout this workflow
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  # Ensure we have a token for API calls
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
echo "Using: $AUTH"
```

### Extracting Owner/Repo from the Git Remote

Many `curl` commands need `owner/repo`. Extract it from the git remote:

```bash
# Works for both HTTPS and SSH remote URLs
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Owner: $OWNER, Repo: $REPO"
```

---

## Lifecycle Steps

- [Branch creation and commits](references/branch-and-commit.md) - naming conventions and Conventional Commits messages.
- [Pushing and creating a PR](references/push-and-create-pr.md) - push the branch, open the PR with gh or curl.
- [Monitoring CI status](references/monitoring-ci.md) - one-shot checks, watch mode, and a curl polling loop.
- [Auto-fixing CI failures](references/auto-fixing-ci.md) - diagnose, fix, push, recheck. Cap at 3 attempts before asking.
- [CI troubleshooting](references/ci-troubleshooting.md) - failure-pattern catalog and the auto-fix decision tree.
- [Merging](references/merging.md) - squash merge, branch cleanup, and auto-merge.
- [Workflow example and command reference](references/workflow-example-and-commands.md) - end-to-end walkthrough plus a gh-vs-curl command table.

## Templates

- [Feature PR body](templates/pr-body-feature.md) - scaffold for a feature PR description.
- [Bugfix PR body](templates/pr-body-bugfix.md) - scaffold for a bug-fix PR description.

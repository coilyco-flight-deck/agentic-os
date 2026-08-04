# Audit checklist: engagement, hijack check, license

Steps 8-10 of the [audit checklist](audit-checklist.md), continued from [`audit-checklist-adoption.md`](audit-checklist-adoption.md). Capture findings into your final writeup.

### 8. Issues and external engagement

`gh issue list --repo <owner>/<name> --state all --limit 30 --json number,state,author,title`

- Are there **external** issue reporters and PR contributors, or only the maintainer + dependabot? Some external engagement = healthy. Zero ever = yellow flag, but acceptable for very young or niche projects.
- How does the maintainer respond? Closed-without-comment patterns are concerning. Hostile replies are a yellow flag for project culture, separate from supply-chain risk.
- Look specifically for closed security issues. Was the disclosure handled responsibly? A maintainer who has handled a disclosure well is a **positive** signal.

### 9. Recent commit pattern (hijack check)

`gh api repos/<owner>/<name>/commits --jq '.[] | "\(.commit.author.email) \(.sha[:8]) \(.commit.message | split("\n")[0])"'`

Look for sudden shifts:

- New committer email addresses showing up in the last 30 days.
- Commit messages that look stylistically inconsistent with the project's history.
- A "small typo fix" that touches build scripts or dependency manifests.
- A version bump or release tagged shortly after a maintainer-account-takeover signal (e.g. avatar change, bio rewrite, weird tweet).

This catches the post-Heartbleed style supply-chain attacks (event-stream, ua-parser-js, etc.). See [`hijack-patterns.md`](hijack-patterns.md).

### 10. License sanity

The license should be MIT, Apache-2.0, BSD, ISC, MPL-2.0, or another OSI-approved permissive/weak-copyleft license. Reject:

- "All rights reserved" / no LICENSE file (don't redistribute).
- Non-OSI-approved custom licenses.
- AGPL/GPL where it would conflict with your project license (most of these are MIT - pulling AGPL contaminates).
- Licenses that grant rights only to specific organizations (some former-OSS projects went this way).

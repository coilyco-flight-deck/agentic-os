# Hijack patterns

A maintainer's account is compromised, or the project is sold to a malicious party, or a "helpful" PR slips a payload past review. Hijacks tend to leave a trail in the commit log.

This file is a checklist of the patterns to scan for during recent-commit review (audit step 9). Most are derived from real incidents.

## Signal 1: Sudden new committer email

Run:

```sh
gh api repos/<owner>/<name>/commits --jq '.[] | "\(.commit.author.date[:10]) \(.commit.author.email)"' | head -50
```

Compare to the historical email set. A previously stable repo with 1-2 committer emails that suddenly gains a new one in the last 30 days warrants a closer look at every commit from that email.

The new email might be legitimate (new contributor onboarded). Look at the commit content:

- New contributor's first PR is a small, scoped change → normal
- New contributor's first commit touches `Cargo.toml`, `package.json`, `setup.py`, or `build.rs` → flag and read carefully
- New contributor's first commit cuts a release → red flag, this is the event-stream pattern

## Signal 2: Stylistic inconsistency

Read the most recent 10 commit messages. Compare the writing style, format, and depth to the historical commit log.

Long-time maintainers have stylistic patterns: conventional-commits prefixes, line lengths, signoff trailers, capitalization. A burst of off-style commits is sometimes harmless (the maintainer is tired, or someone on the team has joined), and sometimes a hijack signal.

## Signal 3: "Small typo fix" that touches manifests

The classic. The actual exploit lives in a one-character change to a build script or a dependency manifest. The PR title says "fix typo in README." Reviewers ack from the title.

Always read the actual diff of any commit that touches:

- `Cargo.toml`, `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Brewfile`
- `build.rs`, `setup.py`, `*-build.gypi`, install hooks
- `.github/workflows/*.yml` - adding a new step that exfiltrates secrets to an attacker-controlled webhook
- `.npmrc`, `.cargo/config.toml`, `pip.conf` - registry redirection

Especially when the PR title or commit message is misleading about scope.

## Signal 4: Tag pushed shortly after maintainer-account changes

If the maintainer's GitHub avatar changed, bio rewrote, or 2FA was disabled in the last 30 days, AND a new release was tagged, escalate.

You can't always see 2FA changes, but avatar / bio changes show up in profile metadata. A version tagged with no corresponding visible PR (release tag pushed direct, no release notes) is also a yellow flag in a project that historically used PR-based releases.

## Signals 5-7, incidents, defense in depth

Ownership-handoff signals, minified/vendored/obfuscated code, "helpful" telemetry endpoints, real-incident write-ups (event-stream, ua-parser-js, xz-utils, rc, colors/faker, PyPI typosquats), and the post-audit defense-in-depth checklist continue in [`hijack-incidents.md`](hijack-incidents.md).

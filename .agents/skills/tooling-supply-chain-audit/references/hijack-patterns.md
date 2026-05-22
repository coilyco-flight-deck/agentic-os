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

## Signal 5: Maintainer tweets / blogs about handing off the project

Real-life pattern: maintainer announces "I'm stepping away, [random handle] is taking over." Random handle then ships a malicious release.

When a project transitions ownership, treat the new maintainer as a fresh entity in this audit. Apply the full checklist to them. Don't inherit the trust score of the previous maintainer.

## Signal 6: Minified, vendored, or obfuscated code

Vendored dependencies, minified JS bundles, base64-encoded blobs, "compiled" generated code committed to source - all of these are places where a payload can hide. Audit the source-of-truth, not the artifact.

If a `dist/` folder is committed, look at `src/` and ensure the `dist/` is reproducible from source. If it's not (e.g. random build outputs of unknown provenance), that's a red flag for the project's hygiene at minimum and a potential payload site at worst.

## Signal 7: New maintainer adding a "helpful" telemetry endpoint

Real-world incident pattern: a new maintainer ships a release that includes a "phone-home" call ("we just want to count installs!"). Even if the intent is benign, telemetry endpoints in build scripts or runtime startup code are unacceptable for a library - they're consent-bypassing exfil channels.

Surface this even when intent looks benign. The dep should be added to your audit-rejected list and the user should be told.

## Real incidents to reference

When in doubt, search for these incident write-ups for pattern reminders:

- **event-stream** (npm, 2018) - minor maintainer added; cryptocurrency-stealer payload introduced.
- **ua-parser-js** (npm, 2021) - maintainer's npm account stolen; coinminer payload published.
- **xz-utils backdoor** (2024) - multi-year social-engineering campaign; obfuscated payload in release tarballs but not the git source.
- **rc** (npm, 2021) - typosquat / account takeover; exfil to attacker-controlled webhook.
- **colors / faker** (npm, 2022) - maintainer self-sabotage; not malicious in the security sense but still broke downstream.
- **PyPI mirroring attacks** - typosquatting `requets` for `requests`, etc. Don't just check the existence of the package, check the spelling carefully.

## Defense in depth (post-audit)

Even after a clean audit, add ongoing protection:

- `cargo audit` / `npm audit` / `pip-audit` in CI.
- Dependabot or Renovate enabled, with auto-merge restricted to patch-level updates of already-audited deps.
- Pin to exact versions in production; use ranges only in libraries.
- For load-bearing deps, mirror the source to coilysiren as a fallback in case upstream is hijacked or yanked.

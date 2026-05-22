## Audit checklist

Run every check unless the package is so trivial (e.g. a 50-line MIT-licensed utility crate from a 10-year-old account) that the verdict is obvious. Even then, document which checks you skipped and why.

For each check, capture findings into your final writeup. The writeup is the deliverable.

### 1. Identity and reputation of the org

Use `gh api orgs/<name>` for orgs, `gh api users/<name>` for individuals. Verify:

- Account is real, not a recently-created throwaway. **Account age over 1 year** is a soft floor; under 6 months is a yellow flag, under 30 days is red unless it's an obvious mirror of a long-standing project.
- Public-facing identity matches stated identity. Cross-check `blog`, `homepage`, `email`, `twitter_username`, `bio`. Look for the org's website actually existing.
- Org type makes sense (Organization vs User account; "Organization" alone doesn't mean verified).
- Public_repos count is non-zero and the repos look real, not all-empty.
- For *named individuals* mentioned in the bio: search for them. AWS Heroes, IETF authors, OSS maintainers of well-known projects, conference speakers all leave fingerprints. If the bio claims a named credential ("AWS ML Hero", "IETF chair", "Apache committer"), spot-check at least one.

### 2. Maintainer activity

Use `gh api repos/<owner>/<name>/contributors` and `gh api repos/<owner>/<name>/commits`.

- Top contributor's account age, follower count, and other-repo activity. Drive-by contributors count for nothing; look at the **top 1-2** committers.
- Email addresses on commits should be consistent and match a real domain. Disposable-mail domains are a yellow flag.
- Most-recent commit date. **Under 12 months** is the bright line for "alive" (matches a "no dead repos" rule). Archived/maintenance-mode banners count as dead even if commits are recent.
- PR-vs-direct-push ratio. A solo maintainer pushing direct to main is fine. A maintainer who appears to merge their own PRs without review is also fine, but note it. A pattern of recent commits from many unverified email addresses to a previously-quiet repo is a hijack signal.

See [`references/maintainer-signals.md`](maintainer-signals.md) for full rubric.

### 3. Repo health artifacts

Use `gh api repos/<owner>/<name>/contents` to list top-level files. Healthy projects have most of these:

- `LICENSE` (and not a confusing dual / weird custom one)
- `CHANGELOG.md` or `RELEASES.md` with real version history
- `.github/workflows/` with CI that actually runs
- `dependabot.yml` or `renovate.json`
- `deny.toml` (cargo) / `audit-ci.json` (npm) / `pip-audit` config - supply-chain hygiene tools
- `SECURITY.md` for non-trivial projects
- `.pre-commit-config.yaml` or equivalent linting config

Missing one or two is fine. Missing all of them on a 5,000-LOC dep is a yellow flag.

### 4. Build scripts and proc macros (Rust-specific, but generalize)

This is the high-leverage check for malicious code. Build scripts run on every consumer's machine.

- **Rust:** Look for `build.rs` at the top level of the crate. Look for any path-dep proc-macro crates (these run at compile time inside rustc). Skim for: network calls (`reqwest`, `ureq`, `curl`, `wget`, sockets), filesystem writes outside `OUT_DIR`, environment-variable exfiltration, `std::process::Command` calls, `unsafe` in odd places.
- **npm:** Check `scripts.preinstall`, `scripts.install`, `scripts.postinstall` in `package.json`. These run on `npm install`. Same red flags as build.rs.
- **Python:** Check `setup.py` for non-trivial code (rare in modern projects; `pyproject.toml` is safer). Check `pyproject.toml` for `[tool.poetry.scripts]` or `[project.scripts]` entries that point at suspicious binaries.
- **Go:** Look for `go:generate` directives that shell out to non-standard tools. Check for `init()` functions in published packages that do anything beyond simple registration.

If build scripts exist, **read them**. Don't just confirm they exist.

See [`references/build-script-redflags.md`](build-script-redflags.md) for concrete patterns.

### 5. Dependency tree

For Rust: read the package's full `Cargo.toml`. For npm: `package.json` plus a sanity check on `package-lock.json` if available.

- Are transitive deps from well-known maintainers (tokio-rs, hyperium, serde-rs, dtolnay, etc.)? Or do they pull from random forks?
- Any `path = "../foo"` or `git = "..."` deps that bypass the registry? Flag every one. A well-maintained project sometimes uses path deps for in-tree workspace crates (fine); a published crate that pulls from a contributor's fork-of-a-fork is a red flag.
- Total dep count. If a 200-line utility crate pulls in 80 transitive deps, ask why.

### 6. Downstream adoption

- **crates.io reverse deps:** `curl -s "https://crates.io/api/v1/crates/<name>/reverse_dependencies?per_page=20"` then read `meta.total`. Single-digit reverse deps on a young crate is normal; zero is a yellow flag for anything claiming "production-ready."
- **GitHub code search:** `gh search code "<crate-name>::" filename:Cargo.toml --limit 30` - counts unique repos that import the package. Filter out the publisher's own repos.
- **Look for credible third-party adopters.** A recognizable user (a research lab, a university group, a known OSS project, a company you've heard of) is worth a dozen indie users.

### 7. Advisory and security databases

- RustSec Advisory DB: `curl -sL "https://api.github.com/repos/rustsec/advisory-db/contents/crates/<name>"` - 200 means an entry exists, 404 means clean.
- npm advisories: `npm audit` against a project that includes the dep, or `https://github.com/advisories?query=<package-name>+ecosystem%3Anpm`.
- GitHub Security Advisories: `gh api graphql` for `securityAdvisories` on the package's repo.
- For brew formulas, also check the maintainer-tap reputation; for MCP servers, also check whether the server is on Anthropic's curated list at modelcontextprotocol.io.

### 8. Issues and external engagement

`gh issue list --repo <owner>/<name> --state all --limit 30 --json number,state,author,title`

- Are there *external* issue reporters and PR contributors, or only the maintainer + dependabot? Some external engagement = healthy. Zero ever = yellow flag, but acceptable for very young or niche projects.
- How does the maintainer respond? Closed-without-comment patterns are concerning. Hostile replies are a yellow flag for project culture, separate from supply-chain risk.
- Look specifically for closed security issues. Was the disclosure handled responsibly? A maintainer who has handled a disclosure well is a *positive* signal.

### 9. Recent commit pattern (hijack check)

`gh api repos/<owner>/<name>/commits --jq '.[] | "\(.commit.author.email) \(.sha[:8]) \(.commit.message | split("\n")[0])"'`

Look for sudden shifts:

- New committer email addresses showing up in the last 30 days.
- Commit messages that look stylistically inconsistent with the project's history.
- A "small typo fix" that touches build scripts or dependency manifests.
- A version bump or release tagged shortly after a maintainer-account-takeover signal (e.g. avatar change, bio rewrite, weird tweet).

This catches the post-Heartbleed style supply-chain attacks (event-stream, ua-parser-js, etc.). See [`references/hijack-patterns.md`](hijack-patterns.md).

### 10. License sanity

The license should be MIT, Apache-2.0, BSD, ISC, MPL-2.0, or another OSI-approved permissive/weak-copyleft license. Reject:

- "All rights reserved" / no LICENSE file (don't redistribute).
- Non-OSI-approved custom licenses.
- AGPL/GPL where it would conflict with your project license (most of these are MIT - pulling AGPL contaminates).
- Licenses that grant rights only to specific organizations (some former-OSS projects went this way).


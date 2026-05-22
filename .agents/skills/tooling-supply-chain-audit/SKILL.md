---
name: tooling-supply-chain-audit
description: Audit a third-party package, library, dependency, plugin, brew formula, MCP server, or upstream repo before pulling into your code. Confirms org and maintainers are real, code is not malicious, project is maintained, downstream adoption non-zero. Triggers - audit this dep, vet this crate, is this package safe, supply chain audit, trust check, before I add this dependency, deep scan this repo, investigate this org, is this maintainer real, audit before install, check this upstream.
allowed-tools: Bash Read Grep WebFetch
---

# Supply chain audit

Vet a third-party package before it ships in your code. The output is a trust verdict (green / yellow / red) plus a short writeup. Don't recommend "allow" without running the checks.

## When to run

Run this skill BEFORE:

- Adding a new direct dependency to `Cargo.toml`, `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Pipfile`, `Brewfile`, or any other manifest.
- Installing a new MCP server (`claude mcp add`, `~/.claude.json`, or a plugin marketplace install).
- Adding a new GitHub Action (`uses: org/action@vX`) or workflow that pulls a third-party container.
- Pulling a new brew tap or formula.
- Cloning and running an upstream repo the user found in a search result, blog post, or social link.
- The harness denies a `cargo fetch` / `npm install` / `pip install` / similar action with a "guessed external dependency" or "untrusted external code" error.
- the user says "audit this," "vet this," "deep scan this," "is this real," or "should I trust this."

Skip this skill for:

- Bumping an existing pinned version of a dep that is already trusted (handled by dependabot review, not a fresh audit).
- Pulling from a known/trusted repo or registry.
- One-off `gh api` / `curl` reads of public docs.

## Verdict scale

- **Green** - Allow. Proceed normally. Ordinary maintenance risk (any dep can rot or get compromised later); use `cargo audit` / `npm audit` / dependabot for ongoing watch.
- **Yellow** - Allow with caveats. Document the yellow flags in the audit writeup so future-you knows the soft spots. Examples: bus factor of 1, very young project, single small maintainer.
- **Red** - Stop. Do not add. Surface findings to the user. Examples: typosquat, code suggests data exfiltration, account hijack signals, abandoned with no path forward, license mismatch with project.

## Audit checklist

The full multi-step checklist (org reality, maintainer signals, repo health, code review, downstream adoption, supply-chain risk patterns, build-script red flags, hijack patterns) lives in [`references/audit-checklist.md`](references/audit-checklist.md), with deeper-detail companions in [`references/maintainer-signals.md`](references/maintainer-signals.md), [`references/build-script-redflags.md`](references/build-script-redflags.md), and [`references/hijack-patterns.md`](references/hijack-patterns.md).
## How to invoke `cargo` / `npm` / etc. above board

the environment routes package-manager actions through `coily` to enforce argv validation and audit logging. Bare `cargo` / `npm` / `pip` / `gem` / `bundle` / `pnpm` / `yarn` / `pipx` / `poetry` / `uv` are denied at the lockdown layer. Use the wrapper:

```sh
coily pkg cargo fetch
coily pkg cargo build
coily pkg cargo test
coily pkg npm install
coily pkg pip install <pkg>
```

The wrappers are thin pass-throughs - they take the same args verbatim and only enforce shell-metachar and audit-log discipline. Use them whenever you would have used the bare binary. This applies to every package-manager step in this audit (e.g. `coily pkg cargo audit`, `coily pkg cargo deny check`).

The deny exists because adding a dep means executing untrusted build scripts on the user's machine. The audit (this skill) and the wrapper-based execution are complementary: the audit answers "should this code run at all," the wrapper records "when it ran and what it asked for."

## Output format

Write the audit verdict to chat in this shape, even when the verdict is clean. The structure is what makes it skimmable later when the user re-encounters the same dep.

```markdown
## Verdict: <green | yellow | red>

One-line summary.

## Org / maintainers
- Org: <real? evidence>
- Top contributor: <handle, age, stakes>
- Famous-named credentials verified: <yes / no / n/a>

## Repo health
- Created / last-released / star count
- License
- CI / dependabot / deny.toml / SECURITY.md presence
- Build scripts: <none / reviewed-clean / SUSPICIOUS>

## Supply chain
- RustSec / advisory DB: <clean / entry exists>
- Reverse deps: <count and notable consumers>
- Dependency tree red flags: <none / list>

## Yellow flags worth naming honestly
- <flag 1>
- <flag 2>

## Recommendation
<allow / allow with caveats / decline> + concrete next step.
```

If yellow or red, also document the mitigation to apply (pin a version, add a `[patch.crates-io]` override, scope a denylist entry, schedule a recheck, fork into a controlled namespace).

If saving the audit somewhere durable: drop a note into the project's repo (e.g. `docs/dep-audits/<crate>-<date>.md`) when the dep is non-trivial. For one-off audits the chat record is fine.

## What this skill is NOT

- Not a substitute for `cargo audit` / `npm audit` / `pip-audit`. Those run continuously and catch advisories filed *after* the dep was added. This skill catches "should we have added it in the first place."
- Not a code review. The audit is "is this package roughly trustworthy," not "does this package's API have bugs."
- Not a license review for legal-purposes. License sanity here is "compatible enough to use." For commercial / contributor-license questions, defer to a lawyer.

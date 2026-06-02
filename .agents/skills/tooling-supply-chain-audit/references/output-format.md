# Output format

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

- Not a substitute for `cargo audit` / `npm audit` / `pip-audit`. Those run continuously and catch advisories filed **after** the dep was added. This skill catches "should we have added it in the first place."
- Not a code review. The audit is "is this package roughly trustworthy," not "does this package's API have bugs."
- Not a license review for legal-purposes. License sanity here is "compatible enough to use." For commercial / contributor-license questions, defer to a lawyer.

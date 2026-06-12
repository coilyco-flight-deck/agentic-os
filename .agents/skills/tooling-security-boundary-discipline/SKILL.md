---
name: tooling-security-boundary-discipline
description: Discipline for CLI security boundaries (primarily ward). Names anti-signals and load-bearing properties for designing, evaluating, and maintaining the boundary.
---

# security-boundary-discipline

The practices and anti-signals that came out of ward's security-boundary work. Use this skill to keep prose, runtime, and design moves aligned when modifying any CLI-as-security-boundary surface.

## Triggers

ward, security boundary, threat model, lockdown, SECURITY.md, privileged-ops scope, audit trail, escape-hatch creep, off-host shadows.

## Conventions for filling this out

Per `tooling-skill-authoring`, each substantive section follows the same shape so the why is recoverable on a future cold read:

- **Lead with the rule.** One short imperative or claim.
- **`**Why:**` line.** The incident, constraint, or prior failure mode that produced the rule. Cite the originating commit / issue / dated finding so future readers can judge whether the why is still load-bearing.
- **`**How to apply:**` line.** When the rule fires, what to reach for, what to ignore.
- **Date-stamp where the why is empirical.** "Flagged 2026-05-05 during ward #49" beats an undated assertion.

Sections that are catalogues (anti-signals, references) can be lists; sections that are rules use the three-part shape above.

When a future fill needs structured data (diff SECURITY.md claims against `TestSecurityClaim_*` coverage, walk the ward cli tree and report `SkipPolicy: true` verbs, parse `pkg/lockdown/defaults.yaml`), reach for a committed Python script in this directory rather than encoding the procedure as prompt. The LLM tier should focus on synthesis, not parsing. See the "Bias toward Python helpers" rule in `tooling-skill-authoring`.

## What goes here (when this skill is filled out)

1. **The three load-bearing properties.** Restate the goal in one sentence. Walk each property (privileged-ops scope, escape-hatch resistance, audit trail) and what makes it real vs hopeful.
2. **Anti-signals catalogue.** Phrases that survived previous design rounds because nobody tested them. Each entry pairs the bad phrase with the actual property and the test that pins it. Initial seed: the four anti-signals already in `ward/SECURITY.md` (plumbed-through, summary-as-shadow, drop-then-replace, doc-runtime drift).
3. **Sequencing rules for boundary changes.** Drop / add / refactor each have an order that preserves the boundary mid-flight; doing them in the wrong order creates a degradation gap. Replace-before-drop is the canonical example.
4. **Doc-runtime sync practice.** How the `TestSecurityClaim_*` family in ward works, why it exists, the rule that prose and runtime move together, and the convention that adding a load-bearing claim to `SECURITY.md` requires adding a corresponding test.
5. **Decision template for "is this on the boundary."** A short checklist applied to any new feature ask. Distinguishes "uses the boundary" from "is the boundary."
6. **References.** Pointers into `ward/SECURITY.md`, `pkg/policy`, `pkg/audit`, `pkg/verb`, `pkg/scope`, the security-claims test, and the git-workflow / ops-investigation / writing-system-improvement-vocab skills this one composes with.

## Status

Shell only, deferred. Originating thread is ward issue #49 (closed); the durable artifacts this skill will reference are already in place: the anti-signals section in `ward/SECURITY.md`, the four security commits (`1270bb5`, `6cf5eeb`, `57a0144`, `b29e503`), and the `TestSecurityClaim_*` family at `ward/cmd/ward/security_claims_test.go`. Fill happens in a separate session.

Flagged 2026-05-05.

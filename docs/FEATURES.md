# Features

Major capabilities shipped by `agentic-os`.

This lists shipped capabilities, not files.

## Inventory

- [Shell and secrets](features-shell-secrets.md) - shared shells, Warp, SSM, and GPG.
- [Branded director terminal](alacritty-directors.md) - native Sombra Alacritty launcher.
- [Speech helper](aos-say.md) - `aos-say` client plus relay for status speech.
- **Karabiner key bindings** - external keyboard and Remote Desktop mappings.
- [Agents and sessions](features-agents-sessions.md) - self-name, pulses, status, and harness policy.
- [Agent-compose provider](personality-provider.md) - scoped skills and personality alignment.
- [Agent tool evaluation](../.agents/skills/tooling-agent-tool-evaluation/SKILL.md) - cross-harness tool evals.
- [Role-composed skills](role-composed-skills.md) - role-gated methods and behavioral evaluation.
- [AOS launcher](aos-cli.md) - role and context composition with
  [MCP and tailnet](aos-standalone-connectivity.md),
  [role-gated kubeconfig](aos-kubeconfig.md), and
  [check-ins](aos-acompose-checkin.md).
- [aosguard](aosguard.md) - AOS-specific guarded CLI and generated skill.
- [Code review skill](../.agents/composed/tooling-code-review/COMPOSED.md) - QA-only in-container review stance.
- [Code review contract](../CODE-REVIEW.md) - review invariants.
- [Harness selection](harness-selection.md) - role board, eligibility, Sirens
  routing, and [profiles](local-lane-profiles.md).
- [Test harnesses](test-harness.md) - agent/model smokes and composed-role probes.
- [Issue-corpus discovery index](issue-corpus.md) - offline corpus and live Forgejo lookup.
- [Forgejo Actions logs](forgejo-actions-logs.md) - bounded job logs and whole-run ZIPs.
- [Forgejo Actions list bridge](forgejo-actions-listing.md) - safe first-page helper for Actions run/task inspection.
- [Forgejo runner-token fetch overlay](forgejo-runner-token.md) - guarded runner registration-token minting via fetch leaves.
- [Forgejo Actions rerun bridge](forgejo-actions-rerun.md) - guarded reruns with dispatch fallback and fetch mirror.
- [Ward integration boundary](ward-specs.md) - fixed Ward workflows,
  AOS-owned harness launch tuning, and no role-derived permission bundle.
- [QA verification fixture](qa-verification-fixture.md) - bounded live role proof.
- [Cross-repo tooling and release](features-release-tooling.md) - hooks, diagnostics, promotion, retries, reruns.
- [Telegram CI failure alerts](telegram-ci-alerts.md) - reusable red-channel alerting for failing jobs.
- [dev-base image family](dev-base-image.md) - parallel Ubuntu language images plus the full fan-in surface.
- [CI parity in dev-base](ci-in-dev-base.md) - CI runs inside the moving :release dev-base image.
- [Pull-request CI gate](pr-dev-base-build-validation.md) - repo tests plus affected dev-base image builds without publication.
- [AGENTS pointer](features-agents-pointer.md) - generated sibling-repo workspace pointer.
- [Encoded leak guard](leak-guard.md) - hex-encoded leak-term detector.
- [Context budget](context-budget.md) - role-seat budgets and generated class diffs.
- [AGENTS inventory](agents-context-inventory.md) - fleet corpus and cascades.
- [Mount eligibility](mount-eligibility-manifest.md) - per-harness repository allowlist.
- [Catalog caps reference](catalog-caps-reference.md) - generated numeric caps for validators.
- [Canonical agent-id generator](dictatable-id-alphabet.md) - short lowercase agent IDs.
- [Knowledge-base freshness program](knowledge-base-freshness.md) - age-based doc fact freshness markers.
- [Agent SDK patterns](agent-sdk-patterns.md) - reusable reference patterns for coordination, context, operations, tools, and managed agents.

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - public-safe agent operating rules.
- [.ward/ward.yaml](../.ward/ward.yaml) - allowlisted commands.

Cross-reference convention from [features-release-tooling.md](features-release-tooling.md).

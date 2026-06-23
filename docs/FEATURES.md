# Features

What `agentic-os` does. Cross-platform shell, terminal, and secret-handling for every host Kai runs. Public, generic, leak-safe by construction.

This doc describes capabilities, not files. If you want a file inventory, run `ls`.

## Inventory

- [Shell and secret handling](features-shell-secrets.md) - cross-platform zsh, agent-CLI repo gate (claude/codex/opencode refuse to launch outside a git repo), in-process SSM secret loader, Warp terminal config, GPG-without-disk-passphrases, install surface.
- **Karabiner key binding assets** - `karabiner/*.json` store complex modifications symlinked into Karabiner's local assets directory: Control+Escape -> backtick, a device-scoped left_option <-> left_command swap for the external keyboard, plus a command -> control remap scoped to a frontmost Microsoft Remote Desktop window so Cmd hotkeys pass through to the remote Windows session. Install with `brew install --cask karabiner-elements`; setup steps in [docs/repo-layout.md](repo-layout.md).
- [Agents and sessions](features-agents-sessions.md) - agent self-name, session pulse.
- [Which harness when](harness-selection.md) - the five agent harnesses (Claude, Codex, OpenCode, Aider, Goose) and three model tiers (trivial-local, capable-local, cloud), with a decision guide for picking one.
- [Test harnesses](test-harness.md) - one doc per agent probing a harness+model pairing before trusting it with real work. [Agent compatibility check](agent-compat.md) runs the daily unittest smoke; Goose also ships `ward exec goose-ask`.
- [Goose issue triage](goose-triage.md) - `ward exec goose-triage` runs triage with local Goose+`qwen3-coder:30b`: P0 net, Goose confirm, urgency run-off cut into P0-P4, plus an **automation-mode** axis (`headless`/`interactive`/`consult`, fail-closed), applied as forgejo labels with a per-issue **verdict comment**. Forgejo I/O routes through `ward ops forgejo` (ward-kdl) as the `coilyco-ops` bot from SSM - no `FORGEJO_TOKEN`. Judgments route through `ward exec goose-json` (provider-enforced JSON schema), with failure records ([goose-failure-records.md](goose-failure-records.md)).
- [Cross-repo tooling and release](features-release-tooling.md) - pre-commit baseline, diagnostic helpers, Forgejo-canonical release actions.
- [dev-base container image](dev-base-image.md) - the inner-loop toolchain (uv, pre-commit, node, go, aws cli, claude, codex, goose) published per release to the forgejo registry as `coilyco-flight-deck/agentic-os:<tag>`, multi-arch, pulled by tag in ward. Bakes a **public substrate seed** (bare mirrors of the image-tier reference repos at `/opt/substrate-seed`) so a ward container warms a cold gitcache with no network.
- [Managed AGENTS.md pointer block](features-agents-pointer.md) - org-aware, drift-checked workspace-base pointer rendered into each repo's AGENTS.md.
- [Encoded leak guard](leak-guard.md) - pre-commit hook that rejects plaintext occurrences of awkward-leak terms (employer/partner names, private-to-public references) held as hex and decoded only in memory, so the ruleset is not itself grep-bait.
- [Context-budget report](context-budget.md) - on-demand measure of the eager startup context each harness (claude/codex/opencode) loads vs a per-harness token budget, with per-source attribution, reusing the agent-compose resolution.
- [Mount-eligibility manifest](mount-eligibility-manifest.md) - agent-compose emits `mount-eligibility.json`: per harness, the repos it may mount on this host (`~/projects/<org>/<repo>` paths plus an always-on default set), reusing the composer's scope/harness selection so ward reads the mount decision instead of re-deriving it. Drift-checked.

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - public-safe agent operating rules.
- [.ward/ward.yaml](../.ward/ward.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/agentic-os-kai#313](https://github.com/coilysiren/agentic-os-kai/issues/313).

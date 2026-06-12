# Features

What `agentic-os` does. Cross-platform shell, terminal, and secret-handling for every host Kai runs. Public, generic, leak-safe by construction.

This doc describes capabilities, not files. If you want a file inventory, run `ls`.

## Inventory

- [Shell and secret handling](features-shell-secrets.md) - cross-platform zsh, in-process SSM secret loader, Warp terminal config, GPG-without-disk-passphrases, install surface.
- **Karabiner key binding asset** - `karabiner/control-escape-backtick.json` stores the Control+Escape -> backtick complex modification and is symlinked into Karabiner's local assets directory.
- [Agents and sessions](features-agents-sessions.md) - agent self-name, session pulse.
- [Cross-repo tooling and release](features-release-tooling.md) - pre-commit baseline, diagnostic helpers, Forgejo-canonical release actions.
- [Managed AGENTS.md pointer block](features-agents-pointer.md) - org-aware, drift-checked workspace-base pointer rendered into each repo's AGENTS.md.
- [Encoded leak guard](leak-guard.md) - pre-commit hook that rejects plaintext occurrences of awkward-leak terms (employer/partner names, private-to-public references, dependency-cycle back-references) held as hex and decoded only in memory, so the ruleset is not itself grep-bait.

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - public-safe agent operating rules.
- [.ward/ward.yaml](../.ward/ward.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/agentic-os-kai#313](https://github.com/coilysiren/agentic-os-kai/issues/313).

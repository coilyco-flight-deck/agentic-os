# Features

What `agentic-os` does. Cross-platform shell, terminal, and secret-handling for every host Kai runs. Public, generic, leak-safe by construction.

This doc describes capabilities, not files. If you want a file inventory, run `ls`.

## Cross-platform shell

Single zsh config tree that boots cleanly on Mac, Linux (kai-server), and Windows (Git Bash). Picks the right host file via `uname -s` so there's no manual branching. Symlinked into `~/.zshrc` per host. Carries identity, history, AWS defaults, prompt, git helpers, aliases, an `rg` wrapper, and `COILY_LOCKDOWN_ROOT` for the coily security boundary.

## In-process AWS SSM secret loader

Pull secrets directly into the shell environment, never to disk. `ssm-load` reads every SecureString under the configured prefix and `load-env`s them. `ssm-get <name>` fetches a single value to stdout. Replaces the older cleartext-dump-to-cache pattern with a memory-only path.

## Cross-platform terminal

Single Warp config tree symlinked into `~/.warp/` on Mac and Windows. The repo wins over cloud sync (`is_settings_sync_enabled = false`) so theme, font, vertical tabs, AI/agent toggles, and the secret-redaction regex list stay reproducible across hosts. The redaction surface covers IPv4/IPv6, MAC, AWS keys, GitHub tokens (every variant), Stripe, Firebase, JWT, OpenAI/Anthropic/Fireworks/Google keys, Slack tokens, phone numbers.

## GPG signing without disk-cached passphrases

`gpg-ssm` is a wrapper around `gpg` that pulls the per-host signing-key passphrase from AWS SSM at sign time instead of caching it on disk. Per-host signing keys keep stolen-laptop blast radius bounded. Mac/Linux + Windows (`.cmd` shim for Git for Windows, which can't reliably exec extensionless shebang scripts). Wire it in once with `git config --global gpg.program`.

## Cross-repo pre-commit baseline

Ships the canonical hook IDs that every `coilysiren/*` repo pins via `rev:`: catalog doc-size enforcement, README/AGENTS/FEATURES trifecta presence, documentation layout, code-comment discipline, skill structural validation, dead cross-link detection, `closes #N` commit-msg enforcement, and the `catalog-block-present` check. Consumers don't stamp local copies of the validators; the `agentic-os` Python package is pip-installed into each repo's pre-commit env. Rolled out and audited from `agentic-os-kai`.

## Diagnostic + utility helpers

Small, single-purpose scripts that exist because the failure modes they handle are cryptic by default:

- AWS config linter that catches the `[profile default]` trap (SDKs read `[default]`, misplaced region surfaces later as a useless `NoRegion`).
- Verbatim-echo wrapper that fences command output and clips to mobile-readable size, for the `$$ <cmd>` chat convention.
- GPG signing doctor that walks every check needed to diagnose `failed to sign the data` and names the most-likely fix per failure mode.

## Install surface

[README.md](../README.md) carries per-OS install steps. Mac/Linux use plain `ln -sf`. Windows uses symlinks via Git Bash, which requires Developer Mode + `MSYS=winsymlinks:nativestrict`.

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - agent-facing operating rules (delegates to `agentic-os-kai/AGENTS.md`).
- [.coily/coily.yaml](../.coily/coily.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/agentic-os-kai#313](https://github.com/coilysiren/agentic-os-kai/issues/313).

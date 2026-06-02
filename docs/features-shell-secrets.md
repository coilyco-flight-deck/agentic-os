# Features: shell and secret handling

Cross-platform shell, terminal, and secret-handling capabilities.

## Cross-platform shell

Single zsh config tree that boots cleanly on Mac, Linux (kai-server), and Windows (Git Bash). Picks the right host file via `uname -s` so there's no manual branching. Symlinked into `~/.zshrc` per host. Carries identity, history, AWS defaults, prompt, git helpers, aliases, an `rg` wrapper, and `COILY_LOCKDOWN_ROOT` for the coily security boundary.

## In-process AWS SSM secret loader

Pull secrets directly into the shell environment, never to disk. `ssm-load` reads every SecureString under the configured prefix and `load-env`s them. `ssm-get <name>` fetches a single value to stdout. Replaces the older cleartext-dump-to-cache pattern with a memory-only path.

## Cross-platform terminal

Single Warp config tree symlinked into `~/.warp/` on Mac and Windows. The repo wins over cloud sync (`is_settings_sync_enabled = false`) so theme, font, vertical tabs, AI/agent toggles, and the secret-redaction regex list stay reproducible across hosts. The redaction surface covers IPv4/IPv6, MAC, AWS keys, GitHub tokens (every variant), Stripe, Firebase, JWT, OpenAI/Anthropic/Fireworks/Google keys, Slack tokens, phone numbers.

## GPG signing without disk-cached passphrases

`gpg-ssm` is a wrapper around `gpg` that pulls the per-host signing-key passphrase from AWS SSM at sign time instead of caching it on disk. Per-host signing keys keep stolen-laptop blast radius bounded. Mac/Linux + Windows (`.cmd` shim for Git for Windows, which can't reliably exec extensionless shebang scripts). Wire it in once with `git config --global gpg.program`.

## Install surface

[README.md](../README.md) carries per-OS install steps. Mac/Linux use plain `ln -sf`. Windows uses symlinks via Git Bash, which requires Developer Mode + `MSYS=winsymlinks:nativestrict`.

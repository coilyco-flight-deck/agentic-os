# Repo layout

Full breakdown of what lives where. Summary in [the README](../README.md).

## zsh

- `zsh/zshrc` - top-level entry, symlinked to `~/.zshrc`. Sources `env.zsh`, picks the right `hosts/<os>.zsh`, then `config.zsh` and `ssm-env.zsh`.
- `zsh/env.zsh` - history, identity, editor, AWS defaults, `COILY_LOCKDOWN_ROOT`.
- `zsh/hosts/{macos,linux,windows}.zsh` - per-host PATH and tooling. Picked automatically via `uname -s`.
- `zsh/config.zsh` - aliases, git helpers, `rg` wrapper, prompt (two-line siren motif).
- `zsh/ssm-env.zsh` - in-process AWS SSM secret loader. `ssm-load` reads `/coilysiren/*` into the current shell env. Never disk.

## warp

- `warp/settings.toml` - Warp config. Vertical tabs, theme, font, custom secret-regex list, AI/agent toggles. `[account] is_settings_sync_enabled = false` so the repo wins over cloud sync.
- `warp/tab_configs/startup_config.toml` - default new-tab pane setup.

## scripts

- `verbatim-echo.sh` - wrap a command's output in a fenced block clipped to 20 lines / 100 chars per line. Chat-safe dumps for mobile.
- `check-aws-config.py` - reject the `[profile default]` trap in `~/.aws/config` that surfaces later as a cryptic `NoRegion` from SSM/S3.
- `gpg-ssm` / `gpg-ssm.cmd` - GPG signing wrapper that pulls the passphrase from AWS SSM at `/coilysiren/gpg-passphrase/<keyid>` instead of caching it on disk. The `.cmd` is a bash.exe shim Git for Windows needs because it can't invoke extensionless shebang scripts reliably.
- `check-commit-closes-issue.py` - commit-msg hook rejecting commits that lack a same-repo `closes #N` / `fixes #N` / `resolves #N`.
- `agent-name.sh` - decorate the agent self-name for the Claude Code status line or the SessionStart hook. The name comes from `coily agent-name` with a local fallback when coily is absent.
- `install-agent-name.py` - idempotently wire `agent-name.sh` into `~/.claude/settings.json` as both a status line and a SessionStart hook.
- `session-pulse.sh` - SessionStart hook that cats `~/.cache/agentic-os/session-pulse.yaml` when present, no-op when absent. Any producer writes to that path; the hook is provider-agnostic. YAML so secondary surfaces can reuse the same blob.
- `install-session-pulse.py` - idempotently wire `session-pulse.sh` into `~/.claude/settings.json` as a SessionStart hook.

## skills

`.agents/skills/` - SKILL.md docs for the configs that live here (`tooling-zsh`, `tooling-gpg-ssm`, and the cross-repo skills). agentic-os-kai's `setup.sh` walks this dir as a peer skill source, symlinking each entry into `~/.claude/skills/`. Co-located with the configs they describe so they don't drift.

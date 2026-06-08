# Repo layout

Full breakdown of what lives where. Summary in [the README](../README.md).

## shell

One shared core, two thin per-shell entries, so bash and zsh run identical env, PATH, aliases, functions, and the SSM loader.

- `shell/common.sh` - shared core (bash/zsh common subset). Env + per-OS PATH (picked via `uname -s`), aliases, git helpers, `rg` wrapper, the SSM loader, auto-cd to `~/projects`. Env runs once per terminal tree via the `_SIREN_SHELL_ENV` guard.
- `shell/zshrc` - zsh entry, symlinked to `~/.zshrc`. Sources `common.sh`, then zsh-only bits: `compinit`, the `vcs_info` siren prompt, `warp.zsh`.
- `shell/bashrc` - bash entry, symlinked to `~/.bashrc`. Sources `common.sh`, then bash-only bits: completion, the `PROMPT_COMMAND` siren prompt.
- `shell/warp.zsh` - the zsh-only `warp` dispatcher + completion.
- Host-local overrides: `~/.shellrc.local` (shared, sourced by `common.sh`), `~/.zshrc.local`, `~/.bashrc.local`. Untracked.

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

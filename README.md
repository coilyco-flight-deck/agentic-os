# agentic-os

![Sombra hacking skull](static/wallpaper.jpg)

Cross-platform shell + terminal setup. Zsh on Mac, Linux, and Windows (Git Bash). Warp on Mac and Windows; both configs (`warp/settings.toml`, `warp/tab_configs/startup_config.toml`) symlinked into `~/.warp/`.

## Layout

- `zsh/zshrc` - top-level entry, symlinked to `~/.zshrc`. Sources `env.zsh`, picks the right `hosts/<os>.zsh`, then `config.zsh` and `ssm-env.zsh`.
- `zsh/env.zsh` - history, identity, editor, AWS defaults, `COILY_LOCKDOWN_ROOT`.
- `zsh/hosts/{macos,linux,windows}.zsh` - per-host PATH and tooling. Picked automatically via `uname -s`.
- `zsh/config.zsh` - aliases, git helpers, `rg` wrapper, prompt (two-line siren motif).
- `zsh/ssm-env.zsh` - in-process AWS SSM secret loader. `ssm-load` reads `/coilysiren/*` into the current shell env. Never disk.
- `warp/settings.toml` - Warp config. Vertical tabs, theme, font, custom secret-regex list, AI/agent toggles. `[account] is_settings_sync_enabled = false` so the repo wins over cloud sync.
- `warp/tab_configs/startup_config.toml` - default new-tab pane setup.
- `scripts/` - portable utilities not specific to the shell.
  - `verbatim-echo.sh` - wrap a command's output in a fenced block clipped to 20 lines / 100 chars per line. Chat-safe dumps for mobile.
  - `check-aws-config.py` - reject the `[profile default]` trap in `~/.aws/config` that surfaces later as a cryptic `NoRegion` from SSM/S3.
  - `gpg-ssm` / `gpg-ssm.cmd` - GPG signing wrapper that pulls the passphrase from AWS SSM at `/coilysiren/gpg-passphrase/<keyid>` instead of caching it on disk. Wire-up Mac/Linux: `git config --global gpg.program "$HOME/.local/bin/gpg-ssm"`. Wire-up Windows: same but point at `gpg-ssm.cmd`, a bash.exe shim Git for Windows needs because it can't invoke extensionless shebang scripts reliably.
  - `check-commit-closes-issue.py` - commit-msg hook rejecting commits that lack a same-repo `closes #N` / `fixes #N` / `resolves #N`.
  - `agent-name.sh` - decorate the agent self-name for the Claude Code status line or the SessionStart hook. The name comes from `coily agent-name` (the source of truth) with a local fallback when coily is absent.
  - `install-agent-name.py` - idempotently wire `agent-name.sh` into `~/.claude/settings.json` as both a status line and a SessionStart hook.
  - `session-pulse.sh` - SessionStart hook that cats `~/.cache/agentic-os/session-pulse.yaml` when present, no-op when absent. Any producer (daily skill, cron job, one-off script) writes to that path; the hook is provider-agnostic. Format is YAML so secondary surfaces (statuslines, dashboards) can reuse the same blob without re-parsing prose.
  - `install-session-pulse.py` - idempotently wire `session-pulse.sh` into `~/.claude/settings.json` as a SessionStart hook.
- `.agents/skills/` - SKILL.md docs for the configs that live here. `tooling-zsh`, `tooling-gpg-ssm`. agentic-os-kai's `setup.sh` walks this dir as a peer skill source, symlinking each entry into `~/.claude/skills/`. Co-located with the configs they describe so they don't drift.

## Install

```bash
./setup.sh                # zsh + gpg-ssm symlinks
coily exec warp apply     # warp config (see warp/README.md)
```

`setup.sh` is idempotent. Detects host via `uname -s` and symlinks:

- `~/.zshrc` from `zsh/zshrc` (all hosts)
- `~/.local/bin/gpg-ssm` from `scripts/gpg-ssm` (Mac, Linux) or `scripts/gpg-ssm.cmd` (Windows)

It also runs `install-agent-name.py` to wire the agent self-name into `~/.claude/settings.json` (status line plus SessionStart hook), and `install-session-pulse.py` to wire a second SessionStart hook that surfaces `~/.cache/agentic-os/session-pulse.yaml` if a producer has written one. A status line you set yourself is left untouched.

Pre-existing real files are backed up to `<path>.bak` on first run; later runs replace the symlinks in place.

### Per-host notes

- **Linux (kai-server)** - Login-shell switch is on the operator: `chsh -s "$(command -v zsh)"`.
- **Windows (Git Bash)** - Install zsh via MSYS first: `pacman -S zsh`. Symlinks need either an elevated Git Bash or Settings → Privacy and Security → For developers → Developer Mode toggled on.

After the gpg-ssm symlink lands, wire it into git:

```bash
git config --global gpg.program "$HOME/.local/bin/gpg-ssm"   # Mac, Linux
git config --global gpg.program "$HOME/.local/bin/gpg-ssm.cmd"  # Windows
```

## Secrets pattern

The legacy pattern wrote all SSM SecureStrings to `~/.cache/ssm-env.sh` and sourced it from `.zshenv`. That cleartext-on-disk dump was deleted.

The current pattern:

```bash
ssm-load                          # pull every / parameter into the current shell env
ssm-get /eco/server-api-token     # fetch one value without storing it
```

No disk write at any point. Same call works on Mac, Linux, Windows. AWS profile defaults to `default`; override with `ssm-load <profile> <region>`.

If you want secrets at shell startup, append `ssm-load` to the end of `zsh/config.zsh`. Default behavior is opt-in per shell.

## Credits

- `static/wallpaper.jpg` - Sombra hacking skull, from the [Overwatch](https://overwatch.blizzard.com) Sombra ARG promotional materials, Blizzard Entertainment, circa 2016. All Overwatch art and iconography © Blizzard Entertainment. Used here for personal terminal decoration only.

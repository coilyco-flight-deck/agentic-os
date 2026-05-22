---
name: tooling-zsh
description: Zsh is Kai's default shell on every host (Warp on Mac/Linux, Git Bash on Windows). Standard POSIX-ish syntax with zsh extras (PROMPT_SUBST, vcs_info, typeset -U). Use when drafting shell commands, editing agentic-os/zsh/*, configuring PATH or prompt, loading AWS secrets via ssm-load, debugging zsh startup. Triggers - zsh, zshrc, .zshrc, $PATH, typeset, autoload, vcs_info, precmd, ssm-load, ssm-env, env.zsh, config.zsh, hosts/macos.zsh, prompt, Warp.
---

# Zsh

Kai's shell on every host. Drafted commands should be zsh/bash-compatible.

This is the replacement for `tooling-nushell` after the May 2026 Nushell rollback. If you see references to `agentic-os/nu/` in older notes or commits, that tree is dead and scheduled for deletion (see coilysiren/agentic-os#48).

## Config location

Canonical files live at `~/projects/coilysiren/agentic-os/zsh/`, symlinked to `~/.zshrc` per host:

- **Mac/Linux** - `~/.zshrc -> ~/projects/coilysiren/agentic-os/zsh/zshrc`
- **Windows** - same path under Git Bash (zsh installed via MSYS `pacman -S zsh`).

Files:

- `zshrc` - top-level entry. Resolves its own dir, then sources the other files in order.
- `env.zsh` - runs first. Sets HISTFILE/HISTSIZE, `$LANG`, `$EDITOR`, AWS defaults, `$COILY_LOCKDOWN_ROOT`.
- `hosts/{macos,linux,windows}.zsh` - per-OS PATH and tooling. Selected via `uname -s` in `zshrc`.
- `config.zsh` - aliases, `def`s (git helpers, rg wrapper, etc.), the two-line siren-motif prompt, direnv hook, lazy `github-token-load`.
- `ssm-env.zsh` - in-process AWS SSM secret loader. `ssm-load` reads `/coilysiren/env/*` into `$env` for the current session only. Never disk.

## Functions ported from the old nu config

Available in any interactive zsh:

- `gt`, `gush`, `..`, `...`, `....` - aliases
- `rg` - wrapper with `--hidden --glob '!.git' --glob '!*.svg' --glob '!.vscode'`
- `git-default-branch`, `git-pr-title`, `git-merge-default-branch`, `git-checkpoint`, `git-squash`, `gt-conflicts`
- `docker-bash <container-name>`, `rg-code <pattern>`, `pull-all-repos`, `count-lines`
- `ssm-load [profile] [region]`, `ssm-get <name> [profile] [region]`
- `github-token-load` - lazy. Call when something needs `$GITHUB_PERSONAL_ACCESS_TOKEN`; not eager on every shell start.

## Prompt

Two-line, mirroring the old nu prompt:

```
🕐 HH:MM:SS  🧜 user@host  📂 cwd  ⚓ branch ✨  💥 N
$
```

- ⚓ branch shows only inside a git repo.
- ✨ marks a dirty working tree.
- 💥 N shows only when the previous command exited non-zero.

Built on `vcs_info` + `PROMPT_SUBST`. No starship dependency.

## Editing

- Edit the file in `~/projects/coilysiren/agentic-os/zsh/` (the symlink resolves there).
- Reload with `exec zsh` in any open shell, or just open a new Warp tab.
- Errors at startup surface immediately. `zsh -x` traces line-by-line if a function silently misbehaves.

## Common edits

- **Add an alias** - drop into the alias block in `config.zsh`.
- **Add a function** - append to `config.zsh`. Keep it portable (POSIX-ish) so Git Bash on Windows runs it too.
- **Change PATH** - host-specific entries go in `hosts/<os>.zsh`. Cross-platform env vars go in `env.zsh`.
- **Change the prompt** - edit `config.zsh`'s `PROMPT=` line. `PROMPT_SUBST` is already on; `vcs_info` is already autoloaded.

## Terminal

Warp is the terminal on every host. Warp has its own settings file at `~/.warp/settings.toml` (managed in-app, not in this repo). zsh config and terminal config are intentionally separate - the same `zsh/` tree should work under any POSIX terminal.

# Install details

Quickstart is in [the README](../README.md). This covers per-host steps and the git gpg wiring.

## What setup.sh symlinks

`setup.sh` is idempotent. It detects the host via `uname -s` and symlinks:

- `~/.zshrc` from `zsh/zshrc` (all hosts)
- `~/.local/bin/gpg-ssm` from `scripts/gpg-ssm` (Mac, Linux) or `scripts/gpg-ssm.cmd` (Windows)

It also runs `install-agent-name.py` to wire the agent self-name into `~/.claude/settings.json` (status line plus SessionStart hook), and `install-session-pulse.py` to wire a second SessionStart hook that surfaces `~/.cache/agentic-os/session-pulse.yaml` if a producer has written one. A status line you set yourself is left untouched.

Pre-existing real files are backed up to `<path>.bak` on first run; later runs replace the symlinks in place.

## Per-host notes

- **Linux (kai-server)** - Login-shell switch is on the operator: `chsh -s "$(command -v zsh)"`.
- **Windows (Git Bash)** - Install zsh via MSYS first: `pacman -S zsh`. Symlinks need either an elevated Git Bash or Settings -> Privacy and Security -> For developers -> Developer Mode toggled on.

## Wire gpg-ssm into git

After the gpg-ssm symlink lands:

```bash
git config --global gpg.program "$HOME/.local/bin/gpg-ssm"      # Mac, Linux
git config --global gpg.program "$HOME/.local/bin/gpg-ssm.cmd"  # Windows
```

# Linux-specific PATH. See docs/zsh-host-files.md for harness allowlist rules.

typeset -U path PATH
path=(
  /home/linuxbrew/.linuxbrew/bin
  /home/linuxbrew/.linuxbrew/sbin
  "$HOME/bin"
  "$HOME/.local/bin"
  "$HOME/.cargo/bin"
  $path
)
export PATH

# linuxbrew shellenv, if installed.
if [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

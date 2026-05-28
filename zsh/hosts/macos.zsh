# Mac-specific PATH and tooling. Sourced after env.zsh.

typeset -U path PATH
path=(
  /opt/homebrew/bin
  /opt/homebrew/sbin
  /usr/local/bin
  /usr/local/sbin
  "$HOME/bin"
  "$HOME/.local/bin"
  "$HOME/.pyenv/shims"
  "$HOME/.cargo/bin"
  /opt/homebrew/opt/ruby/bin
  "$HOME/.gem/ruby/3.4.0/bin"
  /opt/homebrew/opt/openjdk@17/bin
  /opt/homebrew/opt/gradle@7/bin
  /usr/local/share/dotnet
  "$HOME/.fabro/bin"
  $path
)
export PATH

export JAVA_HOME=/opt/homebrew/opt/openjdk@17

# Node: trust the local Caddy root CA for HTTPS dev work, when it exists.
crt="$HOME/Library/Application Support/Caddy/pki/authorities/local/root.crt"
[[ -r "$crt" ]] && export NODE_EXTRA_CA_CERTS="$crt"
unset crt

# brew shellenv resolves MANPATH/INFOPATH alongside PATH.
eval "$(/opt/homebrew/bin/brew shellenv)"

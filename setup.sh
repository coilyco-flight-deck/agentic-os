#!/usr/bin/env bash
# Install host-level config symlinks. See docs/setup.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    HOST=windows
    export MSYS=winsymlinks:nativestrict
    ;;
  Darwin) HOST=mac ;;
  Linux)  HOST=linux ;;
  *) echo "Unsupported host: $(uname -s)" >&2; exit 1 ;;
esac

echo "agentic-os setup"
echo "================"
echo "Host: $HOST"
echo

# Atomic symlink replace. Backs up an existing regular file to <dst>.bak.
ensure_link() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ -L "$dst" ]; then
    rm "$dst"
  elif [ -e "$dst" ]; then
    echo "backed up $dst -> $dst.bak (was a regular file)"
    mv "$dst" "$dst.bak"
  fi
  ln -s "$src" "$dst"
  echo "linked  $dst -> $src"
}

ensure_link "$SCRIPT_DIR/zsh/zshrc" "$HOME/.zshrc"

if [ "$HOST" = "windows" ]; then
  ensure_link "$SCRIPT_DIR/scripts/gpg-ssm.cmd" "$HOME/.local/bin/gpg-ssm.cmd"
else
  ensure_link "$SCRIPT_DIR/scripts/gpg-ssm" "$HOME/.local/bin/gpg-ssm"
fi

if command -v python3 >/dev/null 2>&1; then
  "$SCRIPT_DIR/scripts/install-agent-name.py"
  "$SCRIPT_DIR/scripts/install-session-pulse.py"
else
  echo "skipped agent self-name + session-pulse wiring (python3 not on PATH)"
fi

echo
echo "Done."
current_shell="$(basename "${SHELL:-}")"
if [ "$current_shell" != "zsh" ]; then
  echo "  - Login shell is $current_shell. To switch: chsh -s \"\$(command -v zsh)\""
fi
echo "  - For Warp config, run: coily exec warp apply (see warp/README.md)"

#!/usr/bin/env bash
# agentic-os host setup
#
# Installs the configs that ship in this repo into their host-level homes:
#   - ~/.zshrc                (all hosts)
#   - ~/.local/bin/gpg-ssm    (Mac, Linux)
#   - ~/.local/bin/gpg-ssm.cmd (Windows)
#
# Warp config is owned by `coily exec warp apply` (see warp/README.md), not
# this script.
#
# Idempotent. Run after a fresh clone or after editing a tracked config.
# Windows requires Developer Mode (native symlinks via MSYS=winsymlinks:nativestrict).
#
# Login-shell switch (chsh -s) is left to the operator. It can prompt for a
# password depending on PAM config, so it's not safe to auto-run.

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

# Atomic file/symlink replace. Backs up an existing real file to <dst>.bak.
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

# --- 1. Zsh (~/.zshrc) ---
ensure_link "$SCRIPT_DIR/zsh/zshrc" "$HOME/.zshrc"

# --- 2. gpg-ssm (~/.local/bin/) ---
if [ "$HOST" = "windows" ]; then
  ensure_link "$SCRIPT_DIR/scripts/gpg-ssm.cmd" "$HOME/.local/bin/gpg-ssm.cmd"
else
  ensure_link "$SCRIPT_DIR/scripts/gpg-ssm" "$HOME/.local/bin/gpg-ssm"
fi

# --- 3. Claude Code agent self-name (status line + SessionStart hook) ---
if command -v python3 >/dev/null 2>&1; then
  "$SCRIPT_DIR/scripts/install-agent-name.py"
else
  echo "skipped agent self-name wiring (python3 not on PATH)"
fi

echo
echo "Done."
current_shell="$(basename "${SHELL:-}")"
if [ "$current_shell" != "zsh" ]; then
  echo "  - Login shell is $current_shell. To switch: chsh -s \"\$(command -v zsh)\""
fi
echo "  - For Warp config, run: coily exec warp apply (see warp/README.md)"

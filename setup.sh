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

# Diagnostic + pulse helpers on PATH, .sh suffix dropped so they invoke by bare
# name. check-aws-config ships as a console script, not symlinked here.
for helper in verbatim-echo anthropic-pulse github-pulse git-diff-global; do
  ensure_link "$SCRIPT_DIR/scripts/$helper.sh" "$HOME/.local/bin/$helper"
done

# macOS push-to-talk voice auto-enter. Harmless until Hammerspoon.app runs.
if [ "$HOST" = "mac" ]; then
  ensure_link "$SCRIPT_DIR/hammerspoon/init.lua" "$HOME/.hammerspoon/init.lua"
fi

if command -v python3 >/dev/null 2>&1; then
  "$SCRIPT_DIR/scripts/install-agent-name.py"
  "$SCRIPT_DIR/scripts/install-session-pulse.py"
  # Opt-in: composes the global agent-context file and points each harness's
  # load point at it. No-ops unless ~/.config/agent-compose/agent-compose.yaml
  # exists, so this is inert on hosts that have not opted in.
  PYTHONPATH="$SCRIPT_DIR" python3 -m agentic_os.agent_compose || true
else
  echo "skipped agent self-name + session-pulse wiring (python3 not on PATH)"
fi

# Gate commits in this checkout. Without `pre-commit install` the .pre-commit-config.yaml
# hooks never fire on `git commit`, so commits land unverified. Idempotent.
if command -v pre-commit >/dev/null 2>&1 && git -C "$SCRIPT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  ( cd "$SCRIPT_DIR" && pre-commit install && pre-commit install --hook-type commit-msg )
else
  echo "skipped pre-commit hook install (pre-commit not on PATH or not a git checkout)"
fi

# Warp config is coily-driven. Apply it now when coily is present; otherwise
# leave the hint. The `|| echo` keeps a warp failure from aborting setup.
if command -v coily >/dev/null 2>&1; then
  echo
  echo "Applying Warp config (coily exec warp apply)..."
  coily exec warp apply || echo "  - warp apply failed; run it by hand later (see warp/README.md)"
else
  echo "  - For Warp config, run: coily exec warp apply (see warp/README.md)"
fi

echo
echo "Done."
current_shell="$(basename "${SHELL:-}")"
if [ "$current_shell" != "zsh" ]; then
  echo "  - Login shell is $current_shell. To switch: chsh -s \"\$(command -v zsh)\""
fi

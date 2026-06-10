# shellcheck shell=bash
# Shared bash + zsh init (bash/zsh common subset). See docs/features-shell-secrets.md.

# Env + PATH are inherited, so run once per terminal tree: the exported guard is
# the "has this run in this terminal yet?" check. Aliases/functions always define.
if [ -z "${_SIREN_SHELL_ENV:-}" ]; then
  export _SIREN_SHELL_ENV=1

  export LANG=en_US.UTF-8
  export EDITOR=code
  export GIT_EDITOR=nano
  export SSH_KEY_PATH="$HOME/.ssh/id_rsa"
  export CLI_MFA=ykman
  export AWS_PROFILE=default
  export AWS_REGION=us-east-1
  export AWS_PAGER=""
  export BAT_PAGER=""
  export HISTSIZE=100000
  export SAVEHIST=100000

  # Org-migration: coily owns the bridge root, ward owns the flight-deck root.
  export COILY_LOCKDOWN_ROOT="$HOME/projects/coilyco-bridge"
  export WARD_LOCKDOWN_ROOT="$HOME/projects/coilyco-flight-deck"

  # Prepend $1 to PATH if it's a real dir and not already present.
  _siren_path_prepend() {
    case ":$PATH:" in
      *":$1:"*) ;;
      *) [ -d "$1" ] && PATH="$1:$PATH" ;;
    esac
  }

  case "$(uname -s)" in
    Linux)
      if [ -d "$HOME/.pyenv" ]; then
        export PYENV_ROOT="$HOME/.pyenv"
        _siren_path_prepend "$PYENV_ROOT/bin"
        command -v pyenv >/dev/null && { eval "$(pyenv init --path)"; eval "$(pyenv init -)"; }
      fi
      [ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"
      [ -x /home/linuxbrew/.linuxbrew/bin/brew ] && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
      _siren_path_prepend "$HOME/.local/bin"
      _siren_path_prepend "$HOME/bin"
      export NVM_DIR="$HOME/.nvm"
      [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
      alias ls='ls --color=auto'
      alias grep='grep --color=auto'
      ;;
    Darwin)
      [ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
      for _d in /usr/local/share/dotnet "$HOME/.fabro/bin" /opt/homebrew/opt/gradle@7/bin \
        /opt/homebrew/opt/openjdk@17/bin "$HOME/.gem/ruby/3.4.0/bin" /opt/homebrew/opt/ruby/bin \
        "$HOME/.cargo/bin" "$HOME/.pyenv/shims" "$HOME/.local/bin" "$HOME/bin"; do
        _siren_path_prepend "$_d"
      done
      unset _d
      export JAVA_HOME=/opt/homebrew/opt/openjdk@17
      _crt="$HOME/Library/Application Support/Caddy/pki/authorities/local/root.crt"
      [ -r "$_crt" ] && export NODE_EXTRA_CA_CERTS="$_crt"
      unset _crt
      alias ls='ls -G'
      ;;
    MINGW*|MSYS*)
      for _d in "/c/Program Files/Git/usr/bin" "/c/Program Files/Git/bin" \
        "$HOME/.cargo/bin" "$HOME/.local/bin" "$HOME/bin"; do
        _siren_path_prepend "$_d"
      done
      unset _d
      # Stop msys rewriting leading-slash args before native exes (mangles SSM names).
      export MSYS_NO_PATHCONV=1
      ;;
  esac
  export PATH

  # Shared host-local overrides (machine-specific env, never tracked).
  [ -f "$HOME/.shellrc.local" ] && . "$HOME/.shellrc.local"
fi

# --- Aliases (per shell, always defined) ---
alias del='rm -r'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias gt='git status'
alias gush='git push -u origin HEAD'
alias agent-compose-bat='(cd ~/projects/coilyco-flight-deck/agentic-os && coily exec agent-compose) && bat ~/.config/agent-compose/COMPOSED.{claude,codex}.md'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# --- Functions (per shell, always defined) ---
unalias rg 2>/dev/null || true
rg() {
  command rg --hidden --glob '!.git' --glob '!*.svg' --glob '!.vscode' "$@"
}

unalias bat 2>/dev/null || true
bat() {
  command bat --no-pager "$@"
}

git-default-branch() {
  git symbolic-ref --short refs/remotes/origin/HEAD | sed 's|^origin/||'
}

git-pr-title() {
  PAGER="" gh pr view --json title --jq ".title"
}

source-aos-common() {
  # shellcheck disable=SC1091
  source "$HOME/projects/coilyco-flight-deck/agentic-os/shell/common.sh"
}

pre-commit-aos-version-defined() {
  local version
  version=$(grep -E '^version = ' "$HOME/projects/coilyco-flight-deck/agentic-os/pyproject.toml" | head -1 | sed 's/^version = "\(.*\)"$/\1/')
  echo "$version"
}

pre-commit-aos-version-used() {
  yq -r '.repos[] | select(.repo | test("agentic-os$")) | .rev' \
    "${HOME}/projects/coilyco-flight-deck/agentic-os/.pre-commit-hooks.yaml"
}

pre-commit-hooks-used() {
  yq -r '.repos[] | select(.repo | test("agentic-os$")) | .hooks[].id' \
    "${HOME}/projects/coilyco-${1}/.pre-commit-config.yaml"
}

pre-commit-hooks-defined() {
  yq -r '.[].id' \
    "${HOME}/projects/coilyco-flight-deck/agentic-os/.pre-commit-hooks.yaml"
}

pre-commit-hooks-missing() {
  comm -23 <(pre-commit-hooks-used "${1}"| sort) <(pre-commit-hooks-defined | sort)
}

git-merge-default-branch() {
  local default
  default=$(git-default-branch) || return 1
  git switch "$default" || return 1
  git pull
  git switch -
  git fetch origin "$default"
  git merge "origin/$default"
}

git-checkpoint() {
  local stamp="checkpoint-$(whoami)-$(date +%s)"
  local final="${1:-$stamp}"
  git commit . -m "$final" --allow-empty
  git push -u origin HEAD
}

git-squash() {
  git-merge-default-branch || return 1
  local default branch base
  default=$(git-default-branch) || return 1
  branch=$(git branch --show-current)
  base=$(git merge-base "$default" "$branch")
  git reset "$base"
  git add -A
  git commit . -m "$(git-pr-title)"
  git push -u origin HEAD -f
}

gt-conflicts() {
  git ls-files --unmerged --deduplicate | awk '{print $4}' | sort -u
}

docker-bash() {
  local id
  id=$(docker container ls --filter "name=$1" --quiet)
  docker exec -it "$id" bash
}

rg-code() {
  rg "$1" --files-with-matches | xargs -n1 code
}

# Pull every git repo one level down, returning to the start dir.
pull-all-repos() {
  local start_dir="$PWD" d
  for d in */; do
    if [ -d "$d.git" ]; then
      printf '==> %s\n' "${d%/}"
      git -C "$d" pull
    fi
  done
  cd "$start_dir"
}

count-lines() {
  rg --files | while read -r f; do
    printf '%s\t%s\n' "$(wc -l < "$f")" "$f"
  done | sort -rn
}

# bat every file two levels down: <dir>/*/*
bat-dir() {
  bat "${1:-.}"/*/*
}

# bat every file under a tree, flat. Skips dirs so bat never errors.
bat-tree() {
  tree -fi --noreport "${1:-.}" | while IFS= read -r f; do
    [ -f "$f" ] && printf '%s\0' "$f"
  done | xargs -0 bat
}

# Lazy: call when something needs the token, not at shell start.
github-token-load() {
  GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)
  export GITHUB_PERSONAL_ACCESS_TOKEN
  export HOMEBREW_GITHUB_PACKAGES_USER=coilysiren
  export HOMEBREW_GITHUB_PACKAGES_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN"
}

# --- In-process AWS SSM secret loader (memory only, never disk) ---
ssm-load() {
  local quiet=0
  if [ "$1" = "--quiet" ]; then
    quiet=1
    shift
  fi
  local profile="${1:-default}"
  local region="${2:-us-east-1}"
  local json count name value key
  json=$(AWS_PROFILE="$profile" AWS_REGION="$region" \
    aws ssm get-parameters-by-path --path "/" --recursive --with-decryption \
    --query 'Parameters[].{Name:Name,Value:Value}' --output json) || return 1
  while IFS="$(printf '\t')" read -r name value; do
    key=$(printf '%s' "${name#/}" | tr '/-' '__' | tr '[:lower:]' '[:upper:]')
    export "$key=$value"
  done <<EOF
$(printf '%s' "$json" | jq -r '.[] | [.Name, .Value] | @tsv')
EOF
  count=$(printf '%s' "$json" | jq 'length')
  [ "$quiet" -eq 1 ] || printf 'loaded %s SSM exports into env\n' "$count"
}

ssm-get() {
  local name="$1"
  local profile="${2:-default}"
  local region="${3:-us-east-1}"
  AWS_PROFILE="$profile" AWS_REGION="$region" \
    aws ssm get-parameter --name "$name" --with-decryption \
    --query 'Parameter.Value' --output text
}

# Auto-cd a fresh interactive shell into the projects root (once; a subshell
# already inside it won't re-cd). Guarded so a missing dir never breaks login.
case $- in
  *i*) [ -d "$HOME/projects" ] && [ "$PWD" = "$HOME" ] && cd "$HOME/projects" ;;
esac

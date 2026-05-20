# Aliases, functions, integrations, prompt. Sourced after env.zsh + host file.

# ─── Aliases ──────────────────────────────────────────────────────────────────
alias del='rm -r'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias gt='git status'
alias gush='git push -u origin HEAD'

# rg with the same hidden/glob ignores used in the nu port.
rg() {
  command rg --hidden --glob '!.git' --glob '!*.svg' --glob '!.vscode' "$@"
}

# ─── Git helpers ──────────────────────────────────────────────────────────────
git-default-branch() {
  git symbolic-ref --short refs/remotes/origin/HEAD | sed 's|^origin/||'
}

git-pr-title() {
  PAGER="" gh pr view --json title --jq ".title"
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

# ─── Other ports ──────────────────────────────────────────────────────────────
docker-bash() {
  local id
  id=$(docker container ls --filter "name=$1" --quiet)
  docker exec -it "$id" bash
}

rg-code() {
  rg "$1" --files-with-matches | xargs -n1 code
}

pull-all-repos() {
  local d
  for d in */; do
    if [[ -d "$d.git" ]]; then
      printf '==> %s\n' "$d"
      git -C "$d" pull
    fi
  done
}

count-lines() {
  rg --files | while read -r f; do
    printf '%s\t%s\n' "$(wc -l < "$f")" "$f"
  done | sort -rn
}

# GitHub PAT - lazy. Call when needed; not on every shell start.
github-token-load() {
  GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)
  export GITHUB_PERSONAL_ACCESS_TOKEN
  export HOMEBREW_GITHUB_PACKAGES_USER=coilysiren
  export HOMEBREW_GITHUB_PACKAGES_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN"
}

autoload -Uz compinit && compinit

# Warp ops. `warp launch <name>` opens a launch configuration; `warp list` shows them.
warp() {
  local dir="$HOME/.warp/launch_configurations"
  case "$1" in
    launch)
      if [[ -z "$2" ]]; then
        echo "usage: warp launch <name>" >&2
        return 1
      fi
      open "warp://launch/$2"
      # Fullscreen the new window. The YAML schema has no native fullscreen
      # field, so we fire macOS Ctrl-Cmd-F via System Events after the window
      # has time to appear.
      sleep 0.6
      osascript -e 'tell application "System Events" to tell process "Warp" to keystroke "f" using {control down, command down}' 2>/dev/null
      ;;
    list|ls)
      ls "$dir" 2>/dev/null | sed 's/\.yaml$//'
      ;;
    *)
      echo "usage: warp {launch <name> | list}" >&2
      return 1
      ;;
  esac
}
_warp() {
  local -a verbs configs
  verbs=(launch list ls)
  if (( CURRENT == 2 )); then
    compadd -- $verbs
  elif (( CURRENT == 3 )) && [[ $words[2] == launch ]]; then
    configs=(${(f)"$(ls "$HOME/.warp/launch_configurations" 2>/dev/null | sed 's/\.yaml$//')"})
    compadd -- $configs
  fi
}
compdef _warp warp

# ─── Integrations ─────────────────────────────────────────────────────────────
command -v direnv >/dev/null && eval "$(direnv hook zsh)"

# ─── Prompt ───────────────────────────────────────────────────────────────────
# Two-line prompt matching the old nu version (siren motif). Warp blocks
# render this as a single header above each command.
#
# Line 1: 🕐 HH:MM:SS  🧜 user@host  📂 cwd  ⚓ branch ✨  💥 N
# Line 2: $
autoload -Uz vcs_info
zstyle ':vcs_info:git:*' formats '%b'
zstyle ':vcs_info:git:*' check-for-changes true
zstyle ':vcs_info:git:*' unstagedstr ' %F{yellow}✨%f'
zstyle ':vcs_info:git:*' stagedstr ' %F{yellow}✨%f'

setopt PROMPT_SUBST

precmd() {
  vcs_info
}

PROMPT='%F{cyan}🕐 %D{%H:%M:%S}%f  %F{magenta}🧜 %n%f@%m  %F{blue}📂 %~%f${vcs_info_msg_0_:+  %F{cyan}⚓ ${vcs_info_msg_0_}%f}%(?.. %F{red}💥 %?%f)
%F{magenta}$%f '
RPROMPT=''

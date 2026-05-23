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
# `warp launch <name> <tab-arg>...` runs a single tab's sibling script
# `<name>-<tab-arg-joined-with-->.sh` instead of opening the whole window, so
# pulse/banner tabs can be stopped and restarted standalone.
# `warp tab <color> <title...>` opens a new tab in the current window with the
# given pinned title and ANSI tab color. cwd is inherited from $PWD. Color must
# be one of the 8 ANSI values; Warp's tab_config schema rejects anything else
# (AnsiColorIdentifier enum in warp_core/src/ui/theme/mod.rs).
# `warp theme <slug>` swaps the active color theme. Launch configs carry no
# theme field, so the theme lives in settings.toml's [appearance.themes] block;
# this verb rewrites that block and Warp applies it live (it watches the file).
# `warp theme` with no arg lists the theme YAMLs in ~/.warp/themes/.
warp() {
  local dir="$HOME/.warp/launch_configurations"
  local -a warp_tab_colors
  warp_tab_colors=(black red green yellow blue magenta cyan white)
  case "$1" in
    launch)
      if [[ -z "$2" ]]; then
        echo "usage: warp launch <name> [<tab-arg>...]" >&2
        return 1
      fi
      if (( $# >= 3 )); then
        local name="$2"
        shift 2
        local slug="${(j:-:)@}"
        local yaml="$dir/$name.yaml"
        local source_dir="$(dirname "$(readlink "$yaml" 2>/dev/null || echo "$yaml")")"
        local script="$source_dir/$name-$slug.sh"
        if [[ ! -x "$script" ]]; then
          echo "warp: no such tab script: $script" >&2
          return 1
        fi
        "$script"
        return $?
      fi
      open "warp://launch/$2"
      # Fullscreen the new window. The YAML schema has no native fullscreen
      # field, so we fire macOS Ctrl-Cmd-F via System Events after the window
      # has time to appear.
      sleep 0.6
      osascript -e 'tell application "System Events" to tell process "Warp" to keystroke "f" using {control down, command down}' 2>/dev/null
      ;;
    tab)
      # Writes ~/.warp/tab_configs/wtab.toml fresh on every invocation with
      # title, color, and cwd baked in as literals. Warp re-scans tab_configs/
      # on each URI fire (handle_tab_config_uri calls load_tab_configs), so
      # the fresh write is picked up before the tab opens.
      #
      # Why bake everything: Warp's `title` field is the actual tab title
      # (rendered by render_tab_config; OSC 0 from commands can't override
      # it). The URI handler doesn't thread query params into config params,
      # so handlebars `{{ }}` templating from the URL isn't an option. Baking
      # is the only path to a dynamic title.
      if (( $# < 3 )); then
        echo "usage: warp tab <color> <title...>" >&2
        echo "colors: ${warp_tab_colors[*]}" >&2
        return 1
      fi
      local color="$2"
      shift 2
      local title="$*"
      if [[ ${warp_tab_colors[(Ie)$color]} -eq 0 ]]; then
        echo "warp: invalid color '$color'" >&2
        echo "colors: ${warp_tab_colors[*]}" >&2
        return 1
      fi
      # TOML basic-string escaping: backslash and double-quote.
      local esc_title=${title//\\/\\\\}
      esc_title=${esc_title//\"/\\\"}
      local esc_cwd=${PWD//\\/\\\\}
      esc_cwd=${esc_cwd//\"/\\\"}
      cat >$HOME/.warp/tab_configs/wtab.toml <<TOML
name = "wtab"
title = "$esc_title"
color = "$color"

[[panes]]
id = "main"
type = "terminal"
directory = "$esc_cwd"

[params]
TOML
      open "warppreview://tab_config/wtab"
      ;;
    theme)
      # Swaps the active Warp theme by rewriting the [appearance.themes] block
      # in settings.toml. Warp watches the file and applies the theme live, no
      # relaunch. settings.toml is a symlink into agentic-os/warp/, so the
      # rewrite is done through the symlink (redirection follows it) to avoid
      # replacing the link with a plain file.
      local themes_dir="$HOME/.warp/themes"
      local settings="$HOME/.warp/settings.toml"
      if [[ -z "$2" || "$2" == list ]]; then
        ls "$themes_dir" 2>/dev/null | sed 's/\.yaml$//'
        return 0
      fi
      local slug="$2"
      local yaml="$themes_dir/$slug.yaml"
      if [[ ! -f "$yaml" ]]; then
        echo "warp: no such theme: $slug" >&2
        echo "themes: $(ls "$themes_dir" 2>/dev/null | sed 's/\.yaml$//' | tr '\n' ' ')" >&2
        return 1
      fi
      # Display name is the `name:` field inside the theme YAML.
      local tname=$(sed -n 's/^name:[[:space:]]*//p' "$yaml" | head -1)
      tname=${tname#[\"\']}; tname=${tname%[\"\']}
      local tmp=$(mktemp)
      # Print the section header, drop the new single-line theme assignment,
      # then skip the old assignment until the next blank line or [section].
      # Handles both the multi-line and single-line forms of the old block.
      awk -v name="$tname" -v path="$yaml" '
        /^\[appearance\.themes\]/ {
          print
          print "theme = { custom = { name = \"" name "\", path = \"" path "\" } }"
          skip = 1
          next
        }
        skip && (/^$/ || /^\[/) { skip = 0; print; next }
        skip { next }
        { print }
      ' "$settings" >"$tmp" || { rm -f "$tmp"; return 1; }
      cat "$tmp" >"$settings" && rm -f "$tmp"
      echo "warp: theme -> $tname"
      ;;
    list|ls)
      ls "$dir" 2>/dev/null | sed 's/\.yaml$//'
      ;;
    colors)
      # Valid tab colors per Warp's AnsiColorIdentifier enum
      # (warp_core/src/ui/theme/mod.rs:542). The schema rejects any other
      # value, so this list is the source of truth for `warp tab`.
      print -l -- $warp_tab_colors
      ;;
    *)
      echo "usage: warp {launch <name> [<tab-arg>...] | tab <color> <title...> | theme [<slug>] | colors | list}" >&2
      return 1
      ;;
  esac
}
_warp() {
  local -a verbs configs colors themes
  verbs=(launch tab theme colors list ls)
  colors=(black red green yellow blue magenta cyan white)
  if (( CURRENT == 2 )); then
    compadd -- $verbs
  elif (( CURRENT == 3 )) && [[ $words[2] == launch ]]; then
    configs=(${(f)"$(ls "$HOME/.warp/launch_configurations" 2>/dev/null | sed 's/\.yaml$//')"})
    compadd -- $configs
  elif (( CURRENT == 3 )) && [[ $words[2] == tab ]]; then
    compadd -- $colors
  elif (( CURRENT == 3 )) && [[ $words[2] == theme ]]; then
    themes=(${(f)"$(ls "$HOME/.warp/themes" 2>/dev/null | sed 's/\.yaml$//')"})
    compadd -- $themes
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

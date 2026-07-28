# Temporary attribution rollover marker for agentic-os#773.
# Warp dispatcher (zsh-only: zsh arrays, parameter expansion flags, compdef).
# Sourced by shell/zshrc for interactive zsh. See docs/warp.md.

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
      # Fullscreen via System Events: YAML has no native fullscreen field.
      sleep 0.6
      osascript -e 'tell application "System Events" to tell process "Warp" to keystroke "f" using {control down, command down}' 2>/dev/null
      ;;
    tab)
      # Bakes title/color/cwd into wtab.toml: Warp re-scans on every URI fire.
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
      # Rewrites [appearance.themes] in settings.toml through the symlink.
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
      local tname=$(sed -n 's/^name:[[:space:]]*//p' "$yaml" | head -1)
      tname=${tname#[\"\']}; tname=${tname%[\"\']}
      local tmp=$(mktemp)
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
      # Source of truth: Warp's AnsiColorIdentifier enum rejects others.
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

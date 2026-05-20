#!/usr/bin/env bash
# luca · edit - terminal cwd'd into the repo for text editing.
# Cats README.md so Warp renders relative paths as clickable, opening in the editor.
printf '\n  \033[1mluca · edit\033[0m  ·  text-editing surface\n\n'
[ -f README.md ] && cat README.md

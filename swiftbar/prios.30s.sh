#!/usr/bin/env bash
# SwiftBar plugin: the weekly top-3 priorities, shown in the menu bar.
# Source of truth is ~/.config/prios.txt; see docs/swiftbar-prios.md.

# <bitbar.title>Weekly priorities</bitbar.title>
# <bitbar.desc>Top-3 weekly priorities from ~/.config/prios.txt</bitbar.desc>

export LANG=en_US.UTF-8
PRIOS_FILE="${PRIOS_FILE:-$HOME/.config/prios.txt}"

if [[ ! -f "$PRIOS_FILE" ]]; then
  echo "no prios.txt"
  echo "---"
  echo "Create ~/.config/prios.txt with one priority per line"
  exit 0
fi

# Each line is "label :: description". Menu-bar title is ASCII only (menu-bar
# font tofus emoji/middle-dot): the first word of each label, slash-joined.
title=$(awk -F ' :: ' 'NF && c<3 {c++; split($1,w," "); printf "%s%s", sep, w[1]; sep=" / "}' "$PRIOS_FILE")
echo "${title:-empty}"
echo "---"

# Dropdown (real menu): one line per priority - the description (or the label if
# none). The short label already appears in the menu-bar title, so it is not repeated.
awk -F ' :: ' 'NF && c<3 {c++; printf "%d. %s\n", c, ($2 != "" ? $2 : $1)}' "$PRIOS_FILE"
echo "---"
echo "Edit prios | bash=/usr/bin/open param1=-t param2=$PRIOS_FILE terminal=false"
echo "Refresh | refresh=true"

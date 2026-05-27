#!/usr/bin/env bash
# Run a command, emit chat-safe fenced output. See docs/verbatim-echo.md.
set -o pipefail
echo '```'
"$@" 2>&1 | awk '
  NR<=20 { print substr($0,1,100) }
  NR==21 { print "..."; exit }
'
echo '```'

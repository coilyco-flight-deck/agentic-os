#!/usr/bin/env bash
# session-lattice · pulse - git log watcher until the MCP lands.
# Pulse-tab convention: run against local staging when an MCP exists. Swap this
# to `watch ... mcporter call session-lattice-staging.<verb>` once available.
watch -n 10 'git -C /Users/kai/projects/coilysiren/session-lattice log --oneline -15'

#!/usr/bin/env bash
# session-lattice pulse: git log watcher until the MCP lands.
watch -n 10 'git -C /Users/kai/projects/coilysiren/session-lattice log --oneline -15'

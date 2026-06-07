<!-- Per-harness section override for AGENTS.md, applied to the codex slice only
     by agent-compose (sibling AGENTS.<harness>.md). Codex has no whole-file Read
     tool, so its agents reach for `sed`/`cat`; this rule keeps reads small.
     Claude needs no equivalent: its harness already steers away from raw dumps. -->

## Reading files

Read the slice you need, never the whole file. Locate the relevant lines first with `rg -n PATTERN` (add `-A` / `-B` for surrounding context), then read only that range. Do not dump a file with `sed -n '1,Np'` or `cat` when a few sections are all you want, and do not re-read a file already sitting in context. Tool output persists in every later model request of the session, so one oversized read is paid for many times over - prefer several small targeted reads to one broad dump.

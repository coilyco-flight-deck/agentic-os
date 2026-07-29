# 2026-07-04 - Audit: write+execute ad-hoc /tmp entry points are fenced by the cli-guard engine

Closes agentic-os#236 (migrated from the archived coily#118).

## What the audit asked

coily#118 opened against the old `coily` gate. An agent could write an unreviewed script to `/tmp` and run it, and the worry was the gate's route tables (`coilyRoutes` / `agentGuardRoutes`) missed shapes: `python3 /tmp/x.py`, inline `python3 -c`, package runners (`uv run`), other interpreters (`node`, `ruby`, `perl`), a `chmod +x`'d file run by shebang, absolute-path bypasses like `/usr/bin/python3`. The ask: confirm each is **fenced** - denied or routed through a review wrapper.

## What the audit found

**`coily` is gone** (June 2026 surface reduction, agentic-os#261), so its route tables are not the surface to audit. The gate moved down the layer gradient into **cli-guard's PreToolUse hook engine** (`/substrate/cli-guard/cli/hook/hook.go`) as an **engine-owned, non-configurable deny** a consumer cannot opt out of.

`PreToolUse` runs over **every segment**. `SplitSegments` breaks on `$( )`, `||`, `&&`, `|`, `;`, `&`, and `StripEnvPrefix` peels leading `sudo` / `env VAR=val`, so a denied shape cannot launder behind an allowed prefix, pipe, or substitution. Two engine denies cover the surface:

- **Interpreter invocation** (`interpreterName` + `interpreterTokens`) - basenames the leading token, so `/usr/bin/python3` is denied like bare `python3` (closes the absolute-path bypass). Covers python/ruby/perl/node/deno/bun/php/lua/osascript, the sh/bash/zsh family, powershell/pwsh, cmd, wscript/cscript, mshta. Inline `-c` carries the interpreter as its token, denied too.
- **Scratch-dir execution** (`scratchExec`) - denies running a file resolving under `/tmp`, `/var/tmp`, `/dev/shm`, `/private/tmp`, `/private/var/tmp`, absolute or cwd-relative-from-scratch. Closes the shebang hole where the guard sees only the path. **Writing** to `/tmp` stays allowed, only executing does not.

Both are pinned by tests in `hook_test.go`: `TestPreToolUse_DeniesInterpreterEverySpelling` (bare, `-c`, pipeline-laundered, `&&`, `;`, substitution, absolute path, env-prefixed), `TestPreToolUse_DeniesScratchDirExecution` (the scratch roots, laundered, relative-from-scratch-cwd), `TestPreToolUse_AllowsWritingToScratch`, `TestPreToolUse_SplitsOnShellBoundaries`. The engine's own comments name the "Gap 1 / Gap 2" the audit worried about, so they were closed deliberately.

**Verdict: every write+execute ad-hoc /tmp entry point coily#118 enumerated is fenced at the engine layer** - fenced at the capability layer (deny what it does), not by enumerating names, which is what the [venv-binary bypass finding](security-boundary-deny-uv-venv-bypass.md) recommended.

## Residuals worth tracking, not blocking

- **Package runners and venv console scripts** - `uv run`, `poetry run`, `/repo/.venv/bin/<script>`. Leading token is not an interpreter token or scratch path, so the engine deny does not reach them - same hole as the 2026-05-08 finding. Coverage belongs at the consumer-route layer, per repo. Same class, not /tmp-shaped, so out of this audit's title.
- **Bare scratch token without a slash** - `scratchExec` returns early with no `/` in the token, so a bare `x.sh` via `.`-on-PATH in a scratch cwd would not trip it. Requires `.` on PATH (non-default).

## Rule it produced

When an audit names a gate since retired, it is not moot: the capability moved down the layer gradient, so re-point at wherever it now lives (coily route tables to the cli-guard engine deny), confirm the new home covers every shape the old ask enumerated, then record where coverage stops. For ad-hoc scratch code the durable fence is a capability-layer deny (interpreter-token + scratch-path, per-segment), not a per-name route table, because names have unbounded spellings and capabilities do not.

# Claude Code transcript failure drain

Claude Code tool-use failures land in the same failure-record buffer as Goose
([goose-failure-records.md](goose-failure-records.md)), so the o11y feed is
harness-complete. `ward exec claude-drain`
([scripts/claude_transcript.py](../scripts/claude_transcript.py)) is the drainer.
See agentic-os#249.

## Why the transcript, not a hook

Claude Code **hooks cannot see tool failures** (verified with a PreToolUse +
PostToolUse probe): PostToolUse is success-only, the Bash `tool_response` carries
no exit code, and some client-validated errors (a no-match `Edit`) fire no hook
at all. The reliable source is the **session transcript JSONL** at
`~/.claude/projects/<munged-cwd>/<session-id>.jsonl`, where every tool result
carries a uniform `is_error` flag and the Bash exit code is embedded in the error
text (`Exit code N`).

## The on-disk shape (verified)

A tool result is a `type: "user"` record whose `message.content` holds
`tool_result` blocks `{tool_use_id, is_error, content}` (content a string or a
list of text blocks). The **tool name is not on the result** - it is on the
preceding `type: "assistant"` record's matching `tool_use` block `{id, name,
input}`, so the drainer maps `tool_use_id -> name/input` as it scans. The Bash
command in `input.command` feeds the expected-non-zero classifier.
`isSidechain: true` marks a subagent transcript; those drain the same way.

## What the drain does

1. **Sweep** `~/.claude/projects/**/*.jsonl` (sidechain transcripts included),
   tracking a **per-file byte-offset watermark** in
   `.claude-drain-watermarks.json` under the buffer dir. Only newly-appended
   bytes are re-read, so a re-sweep is idempotent; a file shorter than its
   watermark (rotation) resets to 0.
2. **Classify** each `is_error` result: MCP (`mcp__*`) -> `mcp_error`; a parsed
   `Exit code N` -> `nonzero_exit`; a `<tool_use_error>` wrapper ->
   `edit_no_match` / `file_not_found` / `tool_use_error`; else `tool_error`.
3. **Append** a schema-v1 record to `~/.cache/agentic-os/tool-failures/<repo-slug>.jsonl`
   (slug = git origin at the transcript's `cwd`). No network - the GlitchTip
   shipper is a separate issue.

## Schema v1 mapping

The drainer writes the same schema-v1 line Goose writes, so the shipper consumes
one contract. `harness="claude"`, `source="claude_transcript"`. `schema_title`
and `tool` both carry the tool name (the v1 uniform analog and the `tool` alias
issue #249 names). `exit_code` is parsed from `Exit code N` for Bash, else null.
`attempt` is always 0 (transcripts have no retry notion). `stderr_excerpt` is the
error content tail-capped at 2000 chars. Extra fields: `expected` (classifier
verdict), `is_sidechain`, `session_id`, `record_uuid`. `fingerprint` hashes
(harness, failure_class, tool, normalized signature) reusing Goose's
`_stderr_signature`, so identical failures collapse to one bucket.

## Expected-non-zero classifier

A non-zero exit is not always a failure. The classifier marks `expected: true` on
the benign kinds so genuine failures are not buried - the buffer keeps everything
and emission (issue C) gates on the genuine ones:

- `grep`/`rg`/`egrep`/`fgrep`/`zgrep` with **exit 1** (no match). Exit >= 2 is a
  real grep error and stays genuine.
- `test`/`[`/`diff`/`cmp` with exit 1 (false / differs).
- Any command that tolerates failure with `|| true`.

Pipelines are judged on their **last segment** (the one whose exit code the shell
reports). Only Bash qualifies - every client-validated tool error is genuine.

## Trigger

`ward exec claude-drain` is a **periodic watermark sweep** - the backstop that
works today and tolerates minute latency by design. A timer or a
`SessionEnd`/`Stop` ward hook (`-- --session <id>` drains one session) can fire
it. Wiring the hook depends on ward gaining a non-PreToolUse hook surface; until
then the sweep stands alone. Issue A (schema + buffer) shipped; issue C ships the
buffer to GlitchTip.

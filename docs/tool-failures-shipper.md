# Tool-failure GlitchTip shipper

`ward exec ship-tool-failures` drains the local tool-use failure-record buffer
to GlitchTip so the tool-use error rate becomes a visible, grouped, counted
feed. It is the shipper half of the o11y chain: producers write failure-records,
this drains them. See coilyco-flight-deck/agentic-os#250.

## The buffer it drains

Any harness producer appends schema-v1 failure-records (one JSON object per
line) to a per-repo buffer at `~/.cache/agentic-os/tool-failures/<repo>.jsonl`.
The shipper is producer-agnostic - it ships whatever schema-v1 records exist,
whoever wrote them. Load-bearing fields: `fingerprint` (grouping key),
`failure_class`, `harness`, `repo`, and an optional `expected` classifier flag.

## What a run does

1. **Resolve the DSN** from SSM (`/sentry-dsn/tool-failures`, see
   [SSM.md](../SSM.md)), cached on first success. Absent DSN is fail-soft: the
   run no-ops and the buffer keeps accumulating (nothing is dropped).
2. **Gate** each record on genuine failure - drop any the upstream classifier
   marked `expected` (benign no-match grep, false `test`, `|| true`) and any
   missing `fingerprint`/`failure_class`. The shipper is the final gate.
3. **Emit** one Sentry-protocol envelope per genuine failure. The Sentry
   `fingerprint` is set to the record's own `fingerprint`, so a flood of
   identical failures collapses to one GlitchTip issue with an accurate count -
   the actual signal ("which failure mode dominates"). Tagged by `harness`,
   `failure_class`, `repo`. Volatile detail (stderr excerpt, exit code, session
   id) rides in `extra`, never the low-cardinality title.
4. **Advance a per-file byte watermark** (`.ship-watermarks.json`) line by line,
   so a re-run neither re-ships an accepted event nor loses one after a mid-file
   network error. A file shorter than its watermark (rotation) resets to zero.

## When it runs

Out-of-band from the producers, never on a hot path: a timer or a SessionEnd
ward hook. `-- --dry-run` previews counts without a DSN, POST, or watermark
write; `-- --repo <slug>` narrows to one buffer; `-- --timeout <s>` bounds each
POST.

## Configuration

- `TOOL_FAILURES_DSN` - inject a DSN directly (tests, or before the project
  exists), bypassing SSM.
- `TOOL_FAILURES_DSN_SSM_PATH` - override the SSM parameter path.
- `TOOL_FAILURES_BUFFER_DIR` - override the buffer directory.

## Status

The buffer-and-classify half lands DSN-pluggable and is tested now. Creating the
GlitchTip project and populating `/sentry-dsn/tool-failures` is the one
externally-visible step, confirmed by Kai (agentic-os#250); until then the
shipper fail-softs.

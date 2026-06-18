# Goose failure-record schema v1

Goose's tool-use error rate was unmeasurable by construction. [`goose_json.ask()`](../scripts/goose_json.py) captured `.stderr` / `.returncode` and threw both away, collapsing every failure into one `return None`, and [goose-triage](goose-triage.md) then laundered that `None` into a fail-soft default (unscored -> 30, mode -> consult, run-off keeps issue order). Both layers now keep the evidence. See agentic-os#248.

## ask() instrumentation

Every `ask()` failure writes one classified failure-record (one JSON line) to a per-repo buffer at `~/.cache/agentic-os/tool-failures/<repo-slug>.jsonl`. No network - local buffer only (the GlitchTip shipper is a separate issue). The success path and the `dict | None` return contract are unchanged. Failure classes:

- `timeout` - the call exceeded the timeout (`TimeoutExpired`); `exit_code` null.
- `nonzero_exit` - Goose returned non-zero (where provider 5xx / rate-limit / panic errors surface in stderr).
- `bad_envelope` - the `--output-format json` envelope itself did not JSON-parse.
- `no_schema_valid_message` - the envelope parsed but no assistant message satisfied the schema.
- `exhausted_retries` - a summary record once all N attempts failed.

## Schema v1

One JSON object per line. This is the contract the Claude-transcript drain and the GlitchTip shipper also consume.

- `ts` - int - unix seconds.
- `harness` - str - `"goose"`.
- `source` - str - `"goose_json.ask"`.
- `repo` - str - repo slug (current git origin, or the `repo=` the caller passes).
- `failure_class` - str - one of the classes above.
- `schema_title` - str - the call-site label (`p0_confirm` / `urgency` / `runoff` / `mode` from triage, else the schema/recipe title) - the Goose "tool" analog.
- `exit_code` - int|null - Goose process returncode (null on timeout).
- `attempt` - int - which retry (0-based).
- `stderr_excerpt` - str - truncated Goose stderr (the formerly-discarded evidence), tail-capped at 2000 chars.
- `detail` - str - short message.
- `fingerprint` - str - short hash of (harness, failure_class, schema_title, normalized-stderr-signature). The signature strips volatile tokens (hex, paths, digits) so a flood of identical failures collapses into one counted bucket - the field that answers "which failure mode dominates."

## Triage counts the laundering

The fail-soft defaults stay as resilience, but every substitution from a failed model call is counted per pass in a `goose_failures` block (`p0_confirm` / `urgency` / `runoff` / `mode`), carried in the markdown + yaml report and the terminal summary, separate from the label-write `failed`. So `failed: 0` no longer hides a wrong-but-valid label born of a dead Goose call.

## Out of scope

The Claude Code transcript drain (issue B) and shipping the buffer to GlitchTip (issue C) are separate issues that consume this schema.

"""Ship the local tool-use failure-record buffer to GlitchTip.

Producers (Goose's ``goose_json.ask``, the Claude transcript drain, or any
future harness) append schema-v1 failure-records to a per-repo JSONL buffer at
``~/.cache/agentic-os/tool-failures/<repo-slug>.jsonl``. This package is the
shipper half: it drains that buffer past a per-file watermark, gates on genuine
failures, and emits a Sentry-protocol envelope per failure to GlitchTip
(Sentry-wire-compatible), fingerprinted so a flood of identical failures
collapses to one counted GlitchTip issue.

The shipper is producer-agnostic and DSN-pluggable: it reads whatever schema-v1
records exist and fail-softs (leaving the buffer to accumulate) when the DSN is
absent, so it lands and is testable before any GlitchTip project exists.

See docs/tool-failures-shipper.md.
"""

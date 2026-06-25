# Triage judgment engines

[goose-triage](goose-triage.md) routes every per-issue judgment - P0 confirm, urgency, run-off, mode - through one swappable seam: the `ask(prompt, schema) -> dict | None` callable in [`scripts/triage_engines.py`](../scripts/triage_engines.py). Everything around the seam (pagination, the P0 regex net, the percentile cut, the idempotent labels + create-if-absent verdict comment) is engine-agnostic deterministic scaffolding.

The engine is selectable with `--engine` (or `$AOS_TRIAGE_ENGINE`), so a re-triage with a stronger judge reuses that audited scaffolding instead of being hand-rolled - the motivating papercut in [#271](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/271), where a 2026-06-24 ward re-triage re-implemented the whole pipeline by hand to swap the judge. The active judge names itself in the report line and the verdict-comment footer.

## Built-in engines

- **`goose-json`** (default) - the local Goose + `qwen3-coder:30b` harness via the `goose-json` ward verb ([`goose_json.ask`](../scripts/goose_json.py)): a synthesized Goose recipe whose `response.json_schema` is the call's schema, so the provider enforces a conforming reply, run with the anti-thrash config (`--no-profile --quiet --no-session --max-turns 1`). Each `ask()` failure is classified and buffered (see [goose-failure-records.md](goose-failure-records.md)).
- **`claude`** - the bundled Claude-CLI judge [`scripts/claude_judge.py`](../scripts/claude_judge.py) (`ward exec claude-judge`), which runs `claude -p ... --output-format json` and validates the reply against the schema. Turn-key sugar for `command` over that script. Pin the model with the judge's `--model` (default `opus`) when invoked directly.
- **`command`** - any external judge implementing the goose-json CLI contract: `<cmd> --schema FILE --prompt-file FILE` prints one schema-valid JSON object to stdout, non-zero exit on failure. A cloud-model judge is just such a command. Pass it with `--engine-cmd` (or `$AOS_TRIAGE_ENGINE_CMD`); `--engine-attribution` (or `$AOS_TRIAGE_ENGINE_ATTRIBUTION`) overrides the judge name shown in the report and footer.

## The CLI contract

`goose-json`, `claude-judge`, and any `command` judge share one interface, so they are interchangeable:

```
<judge> --schema FILE (--text STR | --prompt-file FILE)   # prints one JSON object, non-zero exit on failure
```

The `command` engine hands the prompt and the response JSON schema as temp files and reads one JSON object back. Any failure - non-zero exit, unparseable stdout, or a reply missing the schema's required keys - returns `None`, so the pipeline's per-pass fail-soft defaults apply uniformly: a stronger judge gets the same fail-closed treatment as Goose. The per-pass failure tallies in the report count whichever engine ran.

## Usage

```
ward exec goose-triage -- --engine claude                 # re-triage with the live Claude judge
ward exec goose-triage -- --engine command \
    --engine-cmd "uv run python scripts/my_judge.py" \
    --engine-attribution "My Judge v2"                     # any external judge
```

A judge is one process per judgment call (the same shape as the goose-json verb), so an engine that batches or caches across issues is a future refinement, not a contract change.

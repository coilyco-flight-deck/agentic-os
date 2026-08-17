# Test harnesses

A **test harness** probes one agent and model pairing before it is trusted with real work: what the agent claims about itself versus what it can actually do. Each documented probe gets its own `test-harness-<agent>` page. These probes are evidence, not production routing defaults.

This is the parent. Author one child per agent.

## Why per-agent

The probing *mechanism* differs by harness, so the doc does too:

- **Goose** - a wrapper script (`scripts/goose-ask.sh`, ward verb `goose-ask`) runs one-shot questions through `goose run --no-session`.
- **Codex** - `codex exec` invocations (note `--skip-git-repo-check` is needed outside a trusted git repo).
- **OpenCode / Aider** - the harness's own non-interactive run mode against the bound local model.
- **Claude** - cloud, large context, semantic skill-selection - probed differently again.

What stays constant is the *questions* (the probe battery) and the *findings shape* (below), so harnesses can be compared on equal terms.

## Authoring a new harness doc

Name it `test-harness-<agent>.md`, link it from this parent's index, and follow these sections:

- **Mechanism** - exactly how to invoke this agent for one-shot probing, with the gotchas (auth, flags, host).
- **Usage** - the concrete commands, single and batch.
- **First prod-test findings** - run the probe battery once and record what it surfaced, organized by: tool use (what fires, what returns real output), iteration discipline (does it thrash), self-knowledge (model/host self-report accuracy), instruction-following (brevity, format), context window (claimed vs real).
- **Related** - the explicit launch path, runtime configuration, and this parent.

Keep it public-safe: no tower FQDN or opaque ids (use placeholders, resolve at runtime). Findings are point-in-time - date the model/version they were taken against.

## Test harness: Goose

Part of the [test-harness](test-harness.md) doc family - one per agent.

`scripts/goose-ask.sh` (ward verb `goose-ask`) is a minimal probe harness for
Goose. It runs one-shot questions through
`goose run --no-session`, strips the startup banner, times each call, and tees
a full raw transcript under
`~/.cache/agentic-os/goose-ask/<timestamp>.log`. The goal is to interrogate a
Goose+model pairing before trusting it with real work.

The standalone `goose-health` probe was not kept here. Its tower/Ollama reachability and residency checks belong in the always-on agent-health heartbeat in `infrastructure`, which is the canonical place for the serving-layer view.

## Mechanism

`goose run --no-session -t "<question>"` against the bound model in `~/.config/goose/config.yaml` (currently `qwen3-coder:30b` via Ollama on the tower over tailnet). `goose-ask.sh` wraps that with banner stripping, timing, transcript capture, and `-f` batch / `-s` system / `-m` model-override flags.

## Usage

```
ward exec goose-ask -- "a single question"
ward exec goose-ask -- -f scripts/goose-probe.txt        # capability battery
ward exec goose-ask -- -m qwen3:30b-a3b "compare models" # override GOOSE_MODEL
ward exec goose-ask -- -s "Answer in one word." "ping"   # extra system text
```

ward gates repo verbs on a clean working tree, so run the raw script (`bash scripts/goose-ask.sh ...`) while iterating on uncommitted changes. Each question is an independent `--no-session` run, so no state carries between them. Clean answers print to stdout (tool-call rounds included, since they are part of what Goose actually did); the raw log is the source of truth.

`scripts/goose-probe.txt` is the capability battery: it probes what the model *claims* about itself (often wrong) and what the `developer` extension can *actually* do (shell and file tools, exercised live).

## Composed role question probes

`aos-role-question` proves that a projected role can answer through a real model,
not only that its files exist. Each invocation launches one disposable AOS
container, asks one role-specific question, and requires the answer to identify
the role loaded from harness instructions.

## Mechanisms

* **Cloud** - AOS validates Codex file auth before launch, projects the host
  file read-only, copies it into the ephemeral HOME with private permissions,
  and runs Codex read-only with no persisted session. This probe exercises
  authenticated inference rather than only harness startup.
* **Local** - Goose receives its host connection config read-only and runs the
  selected Ollama model without a session.
* **Storage** - the composed agent HOME and `/tmp` are bounded tmpfs mounts. The
  no-substrate provider clone lives under `/tmp`, so initialization consumes no
  shared Docker writable-layer budget and hides no image-owned `/home` tools.
* **Validation** - each run has a ten-minute ceiling and fails unless its output
  contains `ROLE-CONFIRMED: <role>`. Matching ignores case and treats spaces and
  hyphens in role names as equivalent.

The optional third local argument overrides the model for a single probe. The
default is the local design-production model.

Build the launcher and local image before the first run:

```bash
ward exec aos-build
ward exec aos-image-build
```

## Cloud design

```bash
ward exec aos-role-question -- cloud design
```

## Local role matrix

Run these sequentially:

```bash
ward exec aos-role-question -- local engineer
ward exec aos-role-question -- local director
ward exec aos-role-question -- local qa
ward exec aos-role-question -- local ops
ward exec aos-role-question -- local design
ward exec aos-role-question -- local community
ward exec aos-role-question -- local exec
ward exec aos-role-question -- local content
```

Each question targets the role's actual work, such as adversarial verification
for QA, remediation triage for ops, or interaction shaping for design. The
probe never supplies the expected role name in the prompt.

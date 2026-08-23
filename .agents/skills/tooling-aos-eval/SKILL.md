---
name: tooling-aos-eval
description: Grade an eval run with the shared aos-eval CLI - boundary pairing, human annotation, failure taxonomy, and the one-way display export shared by agent-compose and sirens-echo. Triggers - aos-eval, eval grading, annotate a dataset, boundary pair, in-half, out-half, failure taxonomy, eval export, Phoenix display payload.
license: MIT
---

# aos-eval

`aos-eval` is the grading half of the eval stack. agent-compose and sirens-echo
both grade through it, so the pairing rule is implemented once. Committed YAML goes in,
human decisions and one-way display payloads come out. No runner and no model
client live here, so the command never spends a token and never touches a
deployed system. Run `aos-eval help` for the exhaustive reference.

## The rule that makes it worth sharing

A boundary is scored as a **pair**, never as a half. The in-half proves the
rule fires. The out-half proves it does not fire on the neighbouring case that
must still be served. A pair passes only when both halves pass, so a deployment
that refuses everything scores zero rather than fifty percent. Both repos
reinvented this rule independently before the layer was shared.

## Use it

```bash
just aos-eval attributes derive eval/attributes.yaml --out challenges.yaml
just aos-eval attributes check eval/attributes.yaml --dataset run1/dataset.yaml
just aos-eval annotate --dataset run1/dataset.yaml --out run1/annotations.yaml
just aos-eval taxonomy --dataset run1/dataset.yaml --annotations run1/annotations.yaml
just aos-eval export run1 --out run1/display.json
```

Grading saves after every decision, so an interrupted session keeps its work.
A deduction requires a critique and accepts a verbatim evidence span, checked
against the output rather than taken on trust.

## Adopting it in a second repo

Test types, label sets, word caps, and required fields are per deployment.
Declare them in a profile YAML and pass `--profile`, rather than changing the
schema. Without one the built-in agent-compose profile applies.

Install from the repository subdirectory. `main` always resolves. Pin a tag
from the `aos-eval-v*` train instead when a consumer needs reproducibility -
that train advances independently of `aos-precommit`, and its first tag is cut
by `aos-eval-release.yml` on the first promotion that touches `aos-eval/**`.

```bash
uv pip install "aos-eval @ git+https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os.git@main#subdirectory=aos-eval"
```

## What it refuses

`export` stops rather than scrubs when a record looks like it carries a secret,
because the display target is public. A refusal list beats a redaction list: a
record cannot reach a public surface by having one pattern missed. Critique and
evidence are written for the grader and stay out unless `--include-private`
asks for them.

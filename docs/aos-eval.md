# aos-eval

The shared eval grading layer. Two repositories run behavior evals against very different
subjects, and both were implementing the same grading rules separately. `aos-eval` is the half
they now share, packaged at [aos-eval/README.md](../aos-eval/README.md). Run `just aos-eval
help` for the exhaustive command reference, which this page does not restate.

## What is shared and what is not

**Shared here**: the record schema, the boundary pairing rule, the human grading loop, the
failure taxonomy, and the one-way display export.

**Not shared**: the runners. [agent-compose](https://forgejo.coilysiren.me/coilyco-flight-deck/agent-compose)
calls a composed prompt through Agent Proxy and derives its case list from the role roster.
`coilyco-gaming/sirens-echo` drives a live harness against a real tool roster and derives its
case list from a boundary declaration. Neither knows about the other.

That split is the reason the layer exists at all. **No runner and no model client lives here**,
so grading never spends a token and never touches a deployed system. The command reads committed
YAML and writes human decisions.

**Adoption is uneven, and saying so is the point.** agent-compose grades end to end through this
layer. sirens-echo's `eval/boundaries.yaml` is already in the declaration shape, so `boundaries
derive` and `check` read it as-is, but its board dataset keys on `clause`, `history`, and
`current` where `Sample` requires `role`, `test_type`, and `prompt`, so `annotate`, `taxonomy`,
and `export` cannot read a board record until a profile reconciles the two. Until then this page
describes one full consumer and one partial one.

## The rule worth sharing

A boundary is scored as a **pair, never as a half**. The in-half proves the rule fires. The
out-half proves it does not fire on the neighbouring case that must still be served. A pair
passes only when both halves pass, so **a deployment that refuses everything scores zero rather
than fifty percent**.

Both repos arrived at that rule independently before the layer was shared, which is what
qualified it. A rule one consumer invented and the other inherited would have been a dependency
rather than a shared contract.

The out-half is also a negative control. On agent-compose's first graded board the only real
boundary failure was an in-half failure, the case a coverage count reading out-halves alone
would have called perfect.

## Profiles keep the schema still

Test types, their label sets, word caps, and required fields are per deployment. A consumer
declares them in a profile YAML and passes `--profile`, rather than widening the schema for its
own case. Without a profile the built-in agent-compose profile applies.

`Sample` enforces only what is true of every deployment. Everything a deployment adds is
validated against its own profile, so a board whose cases would read as coverage they do not
have is refused rather than accepted with a shrug.

## Grading is resumable and evidence-anchored

Annotation saves after every decision, so an interrupted session keeps its work. A deduction
**requires a critique** and accepts a verbatim evidence span, and that span is **checked against
the output** rather than taken on trust. A critique that quotes text the subject never produced
is a hallucinated justification, and catching it is cheap here and impossible later.

`taxonomy` is the axial step. Critiques are open codes, and it groups them by structural axis
and shared terms into a ranked list of failure modes. **The output is a list of things to fix
rather than a score**, which is what the practitioner literature calls the highest-return
activity in an eval program.

## Export refuses rather than scrubs

`export` projects a committed run into a display payload. **One way, and nothing returns.** The
committed records stay canonical, so any surface reading the payload is a rebuildable projection
rather than a second home for evidence.

The display target is public, so export **stops rather than scrubs** when a record looks like it
carries a secret. It names every reason in one pass and exits non-zero. A refusal list beats a
redaction list: with a scrubber, a record reaches a public surface by having one pattern missed.
Recognized shapes are AWS key ids, bearer and API tokens, JWTs, private key blocks, SSM
parameter paths, Discord snowflakes, tailnet hosts, and email addresses.

Critique and evidence are the grader's own notes, written for the grader, and stay out unless
`--include-private` asks for them. The payload records which way it went. Withheld text is not
scanned, because text that never leaves cannot leak, and refusing on it would block an export
that is safe.

## Running it

```bash
just aos-eval boundaries derive eval/boundaries.yaml --out slots.yaml
just aos-eval boundaries check eval/boundaries.yaml --dataset run1/dataset.yaml
just aos-eval annotate --dataset run1/dataset.yaml --out run1/annotations.yaml
just aos-eval taxonomy --dataset run1/dataset.yaml --annotations run1/annotations.yaml
just aos-eval export run1 --out run1/display.json
just aos-eval-test
```

`boundaries derive` turns a declaration into the slots a board must contain, and `check` names
every missing case, half-authored pair, and case no declaration derived. Both run without a
model, so a consumer can tell coverage from intention before spending anything on a run.

## Adopting it in a third repo

Install from the repository subdirectory. `main` always resolves, and a consumer needing
reproducibility pins a tag from the `aos-eval-v*` train instead.

```bash
uv pip install "aos-eval @ git+https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os.git@main#subdirectory=aos-eval"
```

That train advances independently of `aos-precommit`, cut by `aos-eval-release.yml` on a
promotion touching `aos-eval/**`, so a grading change never forces a hook-suite bump on every
repo in the fleet.

Declare a profile before writing a case. A new deployment's first authored case sets the shape
every case after it copies, so the profile is cheaper to get right than to migrate.

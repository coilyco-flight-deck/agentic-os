# aos-eval

The shared eval grading layer, packaged at [aos-eval/README.md](../aos-eval/README.md). Two repositories
run behavior evals against very different subjects and both were implementing the same grading rules
separately. This is the half they share. `just aos-eval help` is the exhaustive command reference, which
this page does not restate.

## What is shared and what is not

**Shared here**: the record schema, the pairing rule, the human grading loop, the failure taxonomy, and
the one-way display export. **Not shared**: the runners below, and **no runner and no model client lives
here**, so grading never spends a token and never touches a deployed system.

Both consumers are real. sirens-echo's `board-deep` emits `dataset:` with each record carrying a
`Challenge` plus its `output`, so `annotate`, `taxonomy`, and `export` read it with no adapter, and a
contract test there fails if either shape drifts.

## Entity and attribute

A **challenge** tests one **entity** for one **attribute**: in agent-compose a role and a boundary or
personality, in sirens-echo a lane and a clause. `test_type` says which kind and the profile declares the
kinds, so `axis_of` derives an axis rather than enumerating one. `--roster` follows the same rule, taking
`{entity_order, entities: {name: {display_name, purpose, notes}}}` the deployment composed itself.

## The board a run reads

A challenge is answered the same way everywhere: compile a context, send one model call. That holds for a
composed role bundle and for a deployed conversational lane, so `aos-eval.board.v1` carries the **compiled
context** rather than the recipe: `{schema, contexts: {entity: text}, challenges, provenance}`. A challenge
asks with a `prompt` or with `turns`, never both, since a conversational subject is asked with a transcript.

`board check` refuses one that would run incompletely: an unwritten challenge, an entity with no context, a
context no challenge uses. Defining a board is not running one, and this layer still ships no runner.

## The rule worth sharing

A boundary is scored as a **pair, never as a half**. The in-half proves the rule fires. The out-half
proves it does not fire on the neighbouring case that must still be served. A pair passes only when both
halves pass, so **a deployment that refuses everything scores zero rather than fifty percent**.

Both repos arrived at that rule independently, which is what qualified it: a rule one invented and the
other inherited would have been a dependency rather than a contract. The out-half is also a negative
control, and on agent-compose's first graded board the only real failure was an in-half one, which a
coverage count reading out-halves alone would call perfect.

## It measures rather than certifies

`attributes derive` turns a declaration into the unwritten challenges a board must contain, and
`attributes check` compares those to what a dataset wrote, naming every missing one, half-written pair,
and challenge no declaration derived. Both run without a model, so a consumer tells coverage from
intention before spending anything.

**The first honest output in a new repo is usually a gap.** Against sirens-echo's pilot board it reported
56 derived challenges with none written. A coverage report that cannot come back negative is decoration.

## Profiles keep the schema still

Test types, label sets, word caps, and required fields are per deployment. A consumer declares them in a
profile YAML and passes `--profile`, rather than widening the schema for its own case. Without one the
built-in agent-compose profile applies.

`Challenge` enforces only what is true of every deployment, and everything a deployment adds is validated
against its own profile, so a board whose cases would read as coverage they do not have is refused rather
than accepted with a shrug. Declare the profile before the first case: **the first authored case sets the
shape every case after it copies.**

## Grading is resumable and evidence-anchored

Annotation saves after every decision, so an interrupted session keeps its work. A deduction **requires a
critique** and accepts a verbatim evidence span, and that span is **checked against the output** rather
than taken on trust. A critique quoting text the subject never produced is a hallucinated justification,
and catching it is cheap here and impossible later.

`taxonomy` is the axial step. Critiques are open codes, and it groups them by structural axis and shared
terms into a ranked list of failure modes. **The output is a list of things to fix rather than a score.**

## Export refuses rather than scrubs

`export` projects a committed run into a display payload. **One way, and nothing returns**, so any
surface reading it is a rebuildable projection rather than a second home for evidence.

The display target is public, so export **stops rather than scrubs** when a record looks like it carries a
secret, names every reason in one pass, and exits non-zero. A refusal list beats a redaction list: with a
scrubber, a record reaches a public surface by having one pattern missed. Recognized shapes are AWS key
ids, bearer and API tokens, JWTs, private key blocks, SSM parameter paths, Discord snowflakes, tailnet
hosts, and email addresses. Critique and evidence stay out unless `--include-private` asks, and withheld
text is not scanned because text that never leaves cannot leak.

## Running it

`just aos-eval --help` carries the verbs, and the
[skill](../.agents/skills/tooling-aos-eval/SKILL.md) carries the worked sequence: `attributes derive`,
`board check`, `annotate`, `taxonomy`, `export`.

A consumer installs it from this repository's `aos-eval` subdirectory, where `main` always resolves and a
tag from the `aos-eval-v*` train pins a reproducible run. That train advances independently of
`aos-precommit`, cut by `aos-eval-release.yml` on a promotion touching `aos-eval/**`, so a grading change
never forces a hook-suite bump across the fleet.

## The probe layer underneath

Below anything graded sits the cheapest question: does this agent and model pairing do what it claims.
Probes answer that and **produce evidence rather than a verdict**, so a green probe never reads as a
passed science. No pair structure, no human grader, no record a second run compares against.

* **`aos-role-question`** proves a projected role can answer through a real model rather than only that
  its files exist, failing unless the output carries `ROLE-CONFIRMED: <role>`. **The prompt never
  supplies the expected role name.** Invocation and its container bounds are in the
  [skill](../.agents/skills/tooling-aos-eval/SKILL.md).

Findings are point-in-time, so date the model and version each was taken against.

## The two consumers

* [agent-compose evaluation](https://forgejo.coilysiren.me/coilyco-flight-deck/agent-compose/src/branch/main/docs/evaluation.md) -
  a composed prompt through Agent Proxy, cases derived from the role roster.
* [sirens-echo evaluation](https://forgejo.coilysiren.me/coilyco-gaming/sirens-echo/src/branch/main/docs/sirens-echo-science.md) -
  a live harness against a real tool roster, cases authored against prompt clauses.
* [Deleting the Mechanical Scorer](https://coilysiren.me/posts/deleting-the-mechanical-scorer/) - why both
  are hand-graded, and why a rule written twice is what got extracted here.

# Ward orchestration patterns

What Ward formalized about running unattended agents against real repositories. Each entry names the failure it prevents, because that is the part that survives the freeze.

## Admission and identity

* **The durable work record is the reservation authority** - Ward held the issue thread as canonical and treated local reservation files as disposable cache. Anything an operator can delete is not authority. Prevents a cleared cache from silently authorizing a duplicate run.
* **Caller mints the request id before the first dial** - retrying the same id with the same shape returns the existing result, and reusing the id with a different shape is rejected. That is what makes dispatch idempotent under a retry storm.
* **Recheck driftable gates twice** - reservation, branch continuation, pull-request backpressure, and capacity were checked at admission and again immediately before launch, because they drift while a request waits in a queue.
* **A launch intent is not a running agent** - the pre-container lease got its own state so an observer never reads "accepted" as "working".
* **Acceptance is not execution** - `accepted` meant the broker persisted the request and started its worker. It did not mean a container existed or a harness was running.
* **Preview cannot fall back into dispatch** - `--print` rendered the resolved plan and created no durable state, and a launch action carrying `--print` was rejected outright. A dry run that can silently become a real run is not a dry run.
* **Cluster identity is independent of the repository** - a cluster was never resolved from repository metadata, so lifecycle operations could not be aimed by guessing a repo name.

## State and recovery

* **A public state machine with distinct terminal reasons** - `queued`, `accepted`, `launching`, `running`, `cleanup-needed`, `completed`, `blocked`, `failed`, `interrupted`. Collapsing these is how a stuck run reads as a finished one.
* **`blocked` and `failed` are different** - blocked needs outside authority or conditions, failed attempted and did not land. They call for different next actions, so they are different words.
* **`indeterminate` is a real outcome** - when mutation or push state was ambiguous, Ward said so and blocked automated retry pending reconciliation rather than guessing.
* **At-most-one container start per request id** - restart reconciliation replayed pre-container requests, refreshed a stopped container once, adopted a running one, failed an exited one, and treated multiple matching containers as an invariant violation that blocked readiness.
* **Retry eligibility is a property of the terminal state** - `rejected`, `restored`, and `blocked` could retry while the starting revision still matched. `verified` and `indeterminate` could not.
* **Distinct verbs for distinct blast radii** - `stop` targeted one run, `reap` applied policy, `cleanup` removed retained state, `salvage` preserved a remote branch, `rescue` preserved verified Git objects. One verb covering all five hides which one you meant.

## Authority

* **Role selects behavior, never authority** - a role changed prompt and execution behavior only. It could not change credentials, mounts, network, broker grants, merge authority, model, identity, or topology. The estate's boundary model is this pattern generalized.
* **Credential asymmetry by role** - only the broker held the broad credential. Workers received a distinct Git-only credential plus a role-bound capability, and Ward rejected a Git token equal to the broad one. The supervisor held no transferable forge credential at all.
* **Typed operations, never a generic proxy** - writes went through typed issue, pull-request, reservation, workflow, review, dispatch, and QA operations. A generic passthrough would have made every capability check advisory.
* **The broker stamps the sender** - it derived a capability per agent id, authenticated it, and set `from` itself. A caller-supplied sender name was not trusted.
* **Capability does not escalate through descent** - a peer could launch another generic peer but could not select a privileged workflow or call privileged broker actions, and a container-only bundle path could not become a new host mount.
* **Context carries instructions, never permission** - the context bundle manifest rejected any request for permissions, credentials, network, source paths, or capabilities. The producer owned what went in, and Ward owned validation, projection, and teardown.
* **Opaque role slugs for generic peers** - the broker treated role slugs as free context selectors, so a new role needed no change to the fixed roster, while the fixed privileged roles stayed unreachable from that path.

## Evidence

* **Process exit is not completion** - landing required Git or pull-request evidence, and teardown rechecked current evidence before reporting failure. A zero exit code proves the process ended, nothing more.
* **Each workflow names its own evidence** - direct landing required the candidate on remote `main`, pull-request landing required branch plus canonical URL plus submitted state, supervised landing required current CI plus review plus any required verdict plus `merged: true`, and branch-only required the named remote branch.
* **Verification binds to an exact revision** - an independent verdict recorded the revision it reviewed, and the landing gate accepted it only while it still matched the candidate head. A verdict that floats is a verdict for code nobody reviewed.
* **Supervision is read-only and does not orchestrate** - the director read one live snapshot, persisted no orchestration state, and did not poll, rank, triage, choose, dispatch, or redispatch. Repetition and judgment belonged to a harness-native goal.
* **The observer must not assume background polling** - Ward said plainly that a goal must not infer Ward was polling for it. Observation was pull. A loop that believes something is watching on its behalf stops watching.
* **Redact before persistence, and drop rather than scrub** - body-shaped tool arguments and results were dropped whole, not scrubbed in place, with no raw-artifact fallback. A failed drain left `cleanup-needed` instead of claiming success.

## Serialized mutation

* **Compare-and-swap lock, never stolen by age** - a deterministic remote lock ref with exact object-id CAS. A competing attempt was `blocked`, and Ward never deleted a ref whose ownership had changed.
* **Symbolic operation ids, never argv** - the release candidate named operations as safe `area.verb` ids and could not carry argv, scripts, paths, URLs, environment values, credentials, or raw payloads. Naming an operation is not authorizing it, and a separate system did the authorizing.
* **Rollback is a new forward transaction** - never a rewind or a force-replace. A rollback was a fresh candidate to a previous immutable revision, creating and verifying a new child commit.

## See also

* [o2r patterns](o2r-patterns.md) - the wire and coordination half.
* [What does not transfer](does-not-transfer.md) - which of these have no enforcement left.

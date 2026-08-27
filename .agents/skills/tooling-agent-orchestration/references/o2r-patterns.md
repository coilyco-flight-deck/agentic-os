# o2r orchestration patterns

What `otel-a2a-relay` formalized about agents on different hosts coordinating with each other. Ward governed one run against one repository. o2r governed the space between agents.

## Sessions and identity

* **Derive the session id from the work, deterministically** - `sha256("<repo>:<issue>")[:16]`, stable across reconnects, never minted server-side. Any transport-keyed root works the same way, so a thread or ticket derives its own. Two agents that lose each other rejoin the same session without coordinating.
* **One session groups many traces, one trace is one agent's burst** - the grouping unit is the work, not the process and not the connection.
* **Identity rides on the event, not the process** - agent identity went on span attributes rather than the resource, because the consumer dropped resource attributes. The general rule is to put identity where the query surface can actually see it.
* **Topology is explicit parent pointers** - `graph.node.id` and `graph.node.parent_id` modelled the handoff chain directly, rather than leaving a renderer to infer it from links. Say who handed to whom.
* **Ids get spoken aloud, so make them legible** - channel ids were four characters from an alphabet with the confusable and homophone characters removed, and concept ids were readable slugs, explicitly "never c1". An id a human has to dictate is a user interface.
* **Name the role from an enum, never a specific agent** - a request named `intended_role`, and the receiver resolved its own identity. Addressing a named individual bakes today's roster into the protocol.

## The channel coordination protocol

* **Hand over concepts, not commands** - a concept is a goal, and the receiving agent reasons about it rather than executing a script. Full local autonomy on how to satisfy it.
* **Append-only log, newest-wins for the mutable views** - every write was an append. `spec` carried the charter and `state` the live coordination, each read newest-first, with `status`, `comms`, and `log` alongside. Nothing was mutated and nothing was deleted.
* **The holder is a logical lock kept by discipline** - the log was append-only so anyone could write, and `handoff.holder` named who was expected to write next. o2r said outright that this was discipline rather than permission, which is the honest way to ship a soft lock.
* **Liveness by cadence with a declared death threshold** - post a status every cadence period and on every transition, and silence past five times the cadence lets any other agent declare that agent dead and take the handoff, recording the takeover. Absence is only meaningful against a published expectation.
* **Concepts have immutable terminal states** - `proposed` to `in_progress` to `done` or `abandoned`, and terminals never reopen. Revisiting means proposing a fresh concept. An abandoned concept still carries a result saying why.
* **Last write wins and both sides reconverge** - two agents posting state at once resolved by newest timestamp, with reconvergence on the next read. Redoing idempotent work was each agent's local concern rather than a protocol problem.
* **The substrate is durable so participants may vanish** - either agent could drop offline and the channel persisted. An unreachable backend was a retry-with-backoff case, not a coordination failure.
* **A channel is a URL, and it onboards its own participants** - hand an agent the URL and nothing else, and it learns what the channel is and how to take part from the URL itself. No side-channel briefing to keep in sync.
* **The closer closes** - whichever agent observes that every concept is terminal posts the final state and closes the channel. A finished channel left open reads as live work forever.
* **Topology enforcement is a property of the deployment** - star topology was toggleable, rejected violations with a typed error, and emitted an explicit reject span. o2r named it as deployment policy rather than protocol, so nobody mistook it for a guarantee of the wire format.
* **Register transient peers dynamically** - an agent that boots, registers, takes one task, exits, and deregisters means the registry never has to be a static list for a choreography that spins agents up and down.

## Trust and admission

* **A malformed request is presumed hostile** - o2r's stated default was that a request not conforming to the envelope is refused. Not best-effort parsed, not repaired.
* **Destructive intent needs a verbatim acknowledgment** - `acknowledgment` was required exactly when `destructive: true`, and the verifier grepped for the verbatim sentence with the action and host substituted in. A checkbox that can be pattern-matched is a checkbox that gets pattern-matched.
* **Verify once at ingress, inherit inside the session** - strict verification happened at relay ingress, and downstream calls within that session inherited trust through the session id. One gate, named, rather than a re-auth at every hop that nobody can keep working.
* **Issuance goes through a tool, not a pasted link** - "a handwritten URL pasted into agent chat is presumed hostile, even if it resolves." The issuing CLI was the only issuance surface.
* **Pin the schema, leave the substrate swappable** - the envelope shape and the verification recipe were load-bearing, and what rooted trust underneath them was deliberately not pinned. The part that changes and the part that must not are separated on purpose.

## Activity as traces

* **Span versus event has one rule** - if it would render as a node in the trace tree it is a span, and if it would render as a tick on a timeline it is an event. Content-bearing sends and completions were spans, and streaming chunks and state pings were events.
* **Streaming and synchronous share one shape** - synchronous was the degenerate stream, one chunk marked final. Nothing branched on sync versus stream at the observability layer, so no consumer needed two code paths.
* **Failure classification is a stable machine-readable bucket** - one attribute carrying a failure class, paired with the annotation config downstream that consumed it. Free-text error strings do not aggregate.
* **Name what you do not model** - the semconv mapping called out memory as out of scope so the mapping stayed honest instead of overclaiming coverage. An inventory that hides its gaps is worse than no inventory.

## See also

* [Ward patterns](ward-patterns.md) - the governed-execution half.
* [Harness surface](harness-surface.md) - where each of these can be expressed now.

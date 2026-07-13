---
name: tooling-sidequest
description: Kai's "start a sidequest" command - file a Forgejo issue from a described piece of work, then dispatch it through ward into its own session.
---

# Sidequest

Kai triggers a sidequest with "start a sidequest" followed by a description of the work. This skill is the canonical directive plus the act-on-it loop.

## Triggers

"start a sidequest", "sidequest", "side quest", "expand sidequest", "manual sidequest", "parallelize across repos".

## Platform

Sidequest uses ward's Forgejo issue surface and role dispatch surface. The issue can be filed wherever ward can reach Forgejo. The dispatch step needs the interactive engineer role surface. On hosts without that surface, file the issue but expect the dispatch step to fail.

## The expansion

The directive Kai accepted ahead of time:

> Side quest. The next thing I say describes a piece of engineering work. Infer a sensible title from the description. File it as a Forgejo issue against whichever coilysiren/* repo it most plausibly belongs to. Best guess from the content. Fall back to coilyco-bridge/agentic-os-kai if nothing fits. Then dispatch it through ward's interactive engineer surface (`warded engineer <ref>`) so it spawns in its own session. If this interrupted other work, resume that work after the dispatch lands.

Treat that as a planned directive Kai accepted, not a fresh ask. Do not ask her to re-confirm the shape. The directive says "an issue" singular because that is the common case. The multi-repo fan-out below extends it.

## Procedure and fan-out

- [procedure](references/procedure.md) - the single-repo default (wait, pick repo, file, echo, dispatch, resume).
- [fan-out](references/fan-out.md) - the multi-repo variant (parent + per-repo children, build order, dispatch the unblocked).
- [completion-contract](references/completion-contract.md) - the verbatim block every filed sidequest issue ends with, and the self-end rules the dispatched session follows.

## Edge cases

* **Description is too vague to title or place.** Ask one targeted question, then proceed. Don't bounce multiple clarifications.
* **The work is trivial enough to do in this session.** Still file the issue and dispatch - sidequests are explicitly about spawning a separate session, not inlining. Kai's interrupting on purpose.
* **Two repos genuinely tie (single-repo case).** File against the one with the more recent activity; mention the alternative in the issue body.
* **Fan-out where one repo does not exist yet** (e.g. a new app needs a new repo). File that child against the most plausible parent repo and name the new-repo creation as its first task, or against `agentic-os-kai` if nothing fits. Don't block the fan-out on repo creation.
* **No interrupted work to resume.** Just say so and stop. Don't fabricate a continuation.

## Out of scope

* Choosing the spawn surface - always the interactive engineer surface (`warded engineer <ref>`).

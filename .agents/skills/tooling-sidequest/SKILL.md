---
name: tooling-sidequest
description: Manual expansion of Kai's "start a sidequest" Wispr snippet when she can't dictate the full directive. Files a GitHub issue, then coily-dispatches it into its own session.
---

# Sidequest (manual snippet expansion)

Kai's normal flow is to dictate `$$start a sidequest$$` and let Wispr Flow expand the snippet. When she can't verbalize (workshop, public space, sick voice), she'll ask Claude to expand it manually. This skill is the canonical expansion plus the act-on-it loop.

## Triggers

"start a sidequest", "sidequest", "side quest", "expand sidequest", "manual sidequest", "parallelize across repos".

## Platform

Sidequest currently works only on Warp Preview - the `coily dispatch` spawn and the done-banner completion flow depend on Warp Preview behavior. Warp Preview is installed only on the Mac, so Sidequest is Mac-only for now. On other hosts, file the issue but expect the dispatch step to fail.

## The expansion

The snippet body Kai accepted ahead of time:

> Side quest. The next thing I say describes a piece of engineering work. Infer a sensible title from the description. File it as a GitHub issue against whichever coilysiren/* repo it most plausibly belongs to. Best guess from the content. Fall back to coilyco-bridge/agentic-os-kai if nothing fits. Then run `coily dispatch interactive` on the new issue so it spawns in its own session. If this interrupted other work, resume that work after the dispatch lands.

Treat that as a $$...$$ Snippet expansion - a planned directive Kai accepted, not freshly dictated prose. Do not ask her to re-confirm the shape. The snippet text says "an issue" singular because that is the common case. The multi-repo fan-out below extends it. The snippet lives in Wispr Flow and is not edited here.

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

* Editing the snippet itself - that's in Wispr Flow, not here.
* Choosing dispatch mode - always `interactive`.

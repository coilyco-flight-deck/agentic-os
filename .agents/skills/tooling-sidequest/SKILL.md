---
name: tooling-sidequest
description: Manual expansion of Kai's "start a sidequest" Wispr Flow snippet when she cannot verbalize the full directive. File a GitHub issue for the engineering work she describes, then `coily dispatch interactive` so it spawns in its own session. Multi-repo work fans out into a parent issue plus per-repo child issues, each dispatched. Every dispatched issue ships a completion contract - when the work is fully done and autonomous, merge to main and end the session so Warp shows the done banner. Resume interrupted work after. Triggers - "start a sidequest", "sidequest", "side quest", "expand sidequest", "manual sidequest", "parallelize across repos".
---

# Sidequest (manual snippet expansion)

Kai's normal flow is to dictate `$$start a sidequest$$` and let Wispr Flow expand the snippet. When she can't verbalize (workshop, public space, sick voice), she'll ask Claude to expand it manually. This skill is the canonical expansion plus the act-on-it loop.

## Platform

Sidequest currently works only on Warp Preview - the `coily dispatch` spawn and the done-banner completion flow depend on Warp Preview behavior. Warp Preview is installed only on the Mac, so Sidequest is Mac-only for now. On other hosts, file the issue but expect the dispatch step to fail.

## The expansion

The snippet body Kai accepted ahead of time:

> Side quest. The next thing I say describes a piece of engineering work. Infer a sensible title from the description. File it as a GitHub issue against whichever coilysiren/* repo it most plausibly belongs to. Best guess from the content. Fall back to coilysiren/agentic-os-kai if nothing fits. Then run `coily dispatch interactive` on the new issue so it spawns in its own session. If this interrupted other work, resume that work after the dispatch lands.

Treat that as a $$...$$ Snippet expansion - a planned directive Kai accepted, not freshly dictated prose. Do not ask her to re-confirm the shape. The snippet text says "an issue" singular because that is the common case. The multi-repo fan-out below extends it. The snippet lives in Wispr Flow and is not edited here.

## Procedure (single repo - the default)

1. **Wait for the work description.** The trigger phrase alone is not enough - she still needs to describe the actual engineering work. If she hasn't yet, acknowledge briefly and wait.
2. **Decide scope.** Single repo or multi-repo fan-out (see below). Default to single repo. Fan out only when the fan-out trigger is met.
3. **Pick the repo.** Use `data/repo-registry.md` and `data/repo-digests/` to pick the most plausible `coilysiren/*` repo from the content. Fall back to `coilysiren/agentic-os-kai`. Do not ask which repo unless two are genuinely tied.
4. **Infer a title.** Short, imperative, matches the repo's existing issue style. No emojis unless the repo's own issues use them.
5. **File the issue.**
   ```bash
   coily ops gh issue create --repo coilysiren/<repo> --title "<inferred title>" --body-file /tmp/sidequest-body.md
   ```
   Body in Kai's voice rules (no em-dashes, no italics, no semicolons in prose). Quote her description, then add any obvious next-action bullets. End the body with the **completion contract** block (see below) so the dispatched session inherits it. Use `--body-file` - issue bodies routinely contain parens and other shell metacharacters the coily policy gate rejects in inline `--body`.
6. **Echo the issue.** Use the GitHub issue echo format (`[title](url)` + blockquote snippet) so the audit trail lands in chat.
7. **Dispatch.**
   ```bash
   coily dispatch interactive coilysiren/<repo>#<N>
   ```
   Always `interactive` for sidequests - Kai's eyes are on the spawned session. See `kai-coily-dispatch-shorthand` for the dispatch mode rationale.
8. **Resume.** If the sidequest interrupted other work in this session, pick it back up where you left off after the dispatch lands. Name what you're resuming.

## Multi-repo fan-out

**When to fan out.** Either of these:

- Kai says so - "parallelize across repos", "fan this out", "this spans multiple repos", or similar.
- You determine it yourself - the described work spans 2+ `coilysiren/*` repos and the per-repo pieces are each independently filable as a real unit of work. A change that merely touches a second repo in passing is still single-repo. Genuine separate deliverables per repo is fan-out.

**What to do.** Replace steps 3-7 of the single-repo procedure with:

1. **File the parent issue.** An umbrella issue capturing the whole through-line - the goal, the chain, and the per-repo split. File it against the repo that owns the orchestration or the bottom of the dependency chain. This is the design issue a reader lands on first.
2. **File one child issue per repo.** Each child is scoped to exactly that repo's deliverable, in that repo. Title imperative, body quoting the relevant slice of Kai's description plus next-action bullets. Each child body links the parent (`coilysiren/<parent-repo>#<N>`) and ends with the completion contract block. The parent issue does NOT get the block - it is a tracker, never dispatched.
3. **Link children to the parent.** After filing, link each child as a sub-issue of the parent with `coily ops gh` so the parent shows the fan-out tree. If sub-issue linking is unavailable, edit the parent body to list the children as a checklist instead.
4. **Determine build order.** Some fan-outs are fully parallel, some have a dependency chain (build bottom to top). Work it out from the description.
5. **Dispatch the unblocked children.** `coily dispatch interactive` every child whose dependencies are already satisfied - all of them if fully parallel. Children blocked on an earlier child stay filed and linked but are NOT dispatched yet. Note them in chat as blocked-on-`#N`.
6. **Echo everything.** Parent and every child, GitHub issue echo format. State which were dispatched and which are blocked.

Do not dispatch the parent itself - it is a tracking issue, not a unit of work. Step 8 (resume) still applies.

## Completion contract

A sidequest is done when its Warp tab is *visibly* done. Kai dispatches one of these every few minutes. If a finished session just sits idle at a prompt, she has to open the tab and scan for "done" / "finished" - five to ten seconds of hunting, every tab, and at her dispatch rate that adds up to real lost time. A process that has actually exited gives Warp a big red "process exited" banner she catches at a glance while scrolling past. So the dispatched session must end itself (via `coily session end`) when, and only when, the work is genuinely complete.

Every filed sidequest issue (single-repo issue, or each fan-out child - never the parent) ends with this block, verbatim, in the body. It is written with `>` blockquote lines so it nests cleanly inside a Markdown issue body without a fenced code block of its own:

> **Completion contract.** This issue was filed as a sidequest, so its session is expected to finish hands-off. When the work is fully complete and verified - committed, pushed, and merged to `main`, checks green - and it needed no human decision to land (humans can post-review after the fact), do not stop at an idle prompt. End the session by running `coily session end` from a Bash tool call. That verb walks the process ancestry to the `claude` CLI process and signals it, so the session exits cleanly and Warp shows the big red "process exited" banner. The verb is allowlisted because Kai authorized this exact, accurately-named capability, and the audit row records the deliberate end. This is expected and safe: the dangerous failure mode is an agent that resists shutdown, not one that ends itself when its work is done.
>
> Do NOT end the session if the work genuinely needs a human decision before it can land (an irreversible op, a design fork only Kai can call, a blocked dependency). In that case stop at the prompt and say plainly what you need. "Humans can review later" is fine and still self-ends. "A human must decide before merge" is not - leave that session open.

The strictness cuts both ways. Fully autonomous and merged means end the session - leaving it idle is the failure. Genuine human blocker means leave it open - ending it buries the question. The session itself makes that call against its own finished work, not this skill.

## Edge cases

* **Description is too vague to title or place.** Ask one targeted question, then proceed. Don't bounce multiple clarifications.
* **The work is trivial enough to do in this session.** Still file the issue and dispatch - sidequests are explicitly about spawning a separate session, not inlining. Kai's interrupting on purpose.
* **Two repos genuinely tie (single-repo case).** File against the one with the more recent activity; mention the alternative in the issue body.
* **Fan-out where one repo does not exist yet** (e.g. a new app needs a new repo). File that child against the most plausible parent repo and name the new-repo creation as its first task, or against `agentic-os-kai` if nothing fits. Don't block the fan-out on repo creation.
* **No interrupted work to resume.** Just say so and stop. Don't fabricate a continuation.

## Out of scope

* Editing the snippet itself - that's in Wispr Flow, not here.
* Choosing dispatch mode - always `interactive`.

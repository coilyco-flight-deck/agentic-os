---
name: tooling-agent-orchestration
description: Multi-agent orchestration patterns Ward and o2r formalized, kept past their retirement, and how to express each on the harness surface that survives. Use when coordinating several agents, fanning out work, handing off, dispatching background or scheduled work, or designing a coordination protocol. Triggers - orchestration, multi-agent, fan out, subagent, coordinate agents, handoff, dispatch, reservation, agent channel, background task, cron, cross-session.
---

# Agent orchestration

Two subsystems in this estate formalized how autonomous agents coordinate, and both are leaving service.

* **o2r** (`otel-a2a-relay`) is archived. It carried the wire: sessions, handoff, liveness, and agent activity as OTel spans.
* **Ward** is frozen as a contract under [agentic-os#1299](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/1299), with its runtime coming out of CI and the dev-base image. It governed unattended runs: dispatch, reservation, lifecycle, recovery, and landing evidence. Frozen is not deleted, so read that issue for the current posture before assuming anything about the repository.

What they learned does not leave with them. This skill is the inventory.

## The rule this whole skill turns on

**Patterns are durable. Mechanisms are not.** Ward's reservation logic stops enforcing anything once its runtime leaves the hot paths, and the reason it existed does not stop: two dispatchers racing the same work will still collide. A harness tool that looks like a Ward verb is not the Ward verb, because the enforcement underneath it is missing. Read a pattern for the failure it prevents, then ask what enforces it here.

## The patterns

* [Ward patterns](references/ward-patterns.md) - admission and identity, state and recovery, authority, evidence, serialized mutation. What a governed unattended run has to get right.
* [o2r patterns](references/o2r-patterns.md) - sessions and identity, the channel coordination protocol, trust and admission, activity as traces. What agents on different hosts have to agree on.
* [Harness surface](references/harness-surface.md) - the orchestration tools available now, and which pattern each one can and cannot carry.
* [What does not transfer](references/does-not-transfer.md) - the guarantees that stop being enforced once these two leave service. Read this before assuming coverage.

## Four rules that bind every use of the current surface

* **Nothing here is durable.** `CronCreate` writes nothing to disk and dies with the session. Recurring jobs expire after seven days. `Workflow` resume is same-session only. Ward's dispatch was durable, with issue-backed reservations and restart reconciliation, and no harness tool replaces that.
* **Messaging carries no authority.** Asking a peer to do what your own session denied is cross-session permission laundering and the `SendMessage` contract prohibits it. This is the boundary model restated: a seat that defers a boundary does not acquire it by asking a seat that holds it.
* **It is one harness.** This surface is Claude Code. The roster runs seats on codex, openhands, goose, holmesgpt, plandex, hermes, anythingllm, mixpost, penpot, and discord. Anything built on it is unavailable to those seats by construction.
* **Checkpoint discipline does not relax inside a subagent.** Work a subagent produced is work product. A fan-out whose findings live only in a transcript has lost them.

## Provenance

Read from `coilyco-flight-deck/ward` at `040f159` and `coilyco-flight-deck/otel-a2a-relay` at `8b96ed1`, both public. Where a pattern below disagrees with one of those repositories, the repository was right and this file has drifted.

**What Ward's freeze deliberately keeps**, per agentic-os#1299: `.ward/ward.yaml` stays and carries catalog metadata, and the `ward:` AGENTS.md frontmatter key stays as the lane vocabulary, read by composition rather than by any Ward process. The freeze removes a runtime, not a schema.

## See also

* [AGENTS.md](../../../AGENTS.md) - the composed operating base, including command delivery.
* [tooling-agent-workflows](../tooling-agent-workflows/SKILL.md) - documenting an agent-facing CLI, a different subject.

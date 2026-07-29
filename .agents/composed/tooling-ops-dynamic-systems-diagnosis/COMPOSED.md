---
name: tooling-ops-dynamic-systems-diagnosis
description: Use when ops diagnoses ambiguous, intermittent, or distributed system behavior. Builds competing causal models, chooses discriminating signals, and preserves attribution.
low-context: required
---

# Dynamic systems diagnosis

Use this skill when one symptom has several credible causes or behavior changes
over time, load, topology, retries, or dependency state.

## Activation boundary

Ops activates this workflow for ambiguous degradation, feedback loops,
intermittent failures, and cross-service effects. A known failure with a proven
runbook can proceed directly to `tooling-ops-live-remediation`.

## Build competing models

Ops records:

* The user impact, observed symptom, time window, and affected boundary.
* Recent changes and dependency events without treating correlation as cause.
* At least two causal models that could produce the same observation.
* The signal each model predicts and the observation that would weaken it.
* Missing telemetry or inaccessible state that limits confidence.

Ops includes queues, caches, retries, timeouts, saturation, failover, and
control loops when they can amplify or delay the visible symptom. She traces
both the request path and the resource path because failures can propagate
differently through each.

## Choose discriminating evidence

Ops prefers the least invasive observation or reversible probe that separates
the leading models. She changes one variable at a time, predicts the result
before the probe, and records negative evidence as carefully as confirmation.

A useful probe changes the relative probability of competing causes. More logs
are not automatically more information. Ops stops broad log hunting when the
next observation cannot change the decision.

## Preserve time and attribution

Ops aligns signals by event time and accounts for aggregation windows,
sampling, delayed effects, and recovery lag. She does not infer causality from
two metrics sharing a chart shape.

Containment may precede root-cause proof. Ops labels the current result as
symptom relief, causal evidence, or confirmed correction.

## Output contract

The diagnosis brief contains the system boundary, timeline, competing models,
predictions, discriminating evidence, current confidence, and next safe probe.
Any live mutation still follows `tooling-ops-live-remediation` and the active
Ward authority.

## Method provenance

The hypothesis, test, and negative-result loop follows Google SRE's
[effective troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
method.

## Evaluation target

Compare cold and composed ops on latency that could arise from saturation,
retry amplification, or one dependency. Composed ops should model competing
causes, select a discriminating signal, preserve time ordering, and avoid
equating correlated telemetry with proof.

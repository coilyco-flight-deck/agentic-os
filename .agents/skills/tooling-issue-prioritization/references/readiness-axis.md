# Readiness axis: `blocked-on-dependency`

Readiness is orthogonal to priority. It answers whether a correctly scoped issue can run now or must wait for an upstream issue to land. Every issue still requires an interactive human loop. Most issues are ready and need no readiness label.

## The state

- **`blocked-on-dependency`** - the work is correctly scoped but not runnable because its resolver is another repository's issue. It carries a blocker pointer to the upstream issue whose close unblocks it. The pointer lives in the issue body as `<!-- ward-blocked-on: owner/repo#123 -->`. That body marker is the source of truth. Labels alone cannot carry the upstream reference.

## Wake behavior

A dependency block waits for a tracker event rather than for a design decision. When the blocker issue closes, the dependent issue returns to the interactive queue for human-guided work. The wake event never authorizes or starts unattended dispatch.

The `blocked-on-dependency` label rides alongside one P0-P4 priority label. It does not replace priority and does not grant autonomy.

If the blocker pointer is missing or ambiguous, the issue fails closed. The classifier leaves the issue in the ordinary interactive queue and does not claim wake behavior.

## What is named here vs built later

This document names the state and fixes its semantics. Any wake mechanism may surface the dependent issue after its blocker closes, but the mechanism must stop at the interactive queue.

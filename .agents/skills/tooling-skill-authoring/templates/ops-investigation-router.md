---
name: ops-investigation
description: Router across all `ops-investigation-*` skills. Use when starting any investigation that doesn't yet have a clear subject. Triggers - investigate, investigation, debug, root cause, triage, ops, oncall.
---

# Ops Investigation Router

Status: 🗺 Router | Last updated: YYYY-MM-DD

## Routing table

* `ops-investigation-<topic-1>` - one-line description of what this routes to
* `ops-investigation-<topic-2>` - one-line description
* `gaming-eco-investigation` - Eco game-server failures (cross-cluster routing)

## Cross-cutting rules

Rules that apply to every routed-to investigation:

* Pin versions before reasoning about behavior. The version-pin-first discipline lives in the ops-investigation meta-skill.
* Privileged writes route through `coily`, never directly. See the git-workflow and command-passthroughs skills.
* Read-only investigation tools first. Reach for writes only after the investigation has named the failure mechanism.

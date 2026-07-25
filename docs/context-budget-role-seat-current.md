# Current role-seat context inventory

The 11 canonical roles are measured in all four AOS native layouts. Claude and
Codex use the frontier catalog. Goose and OpenCode use the low-context catalog.
The snapshots were generated with released agent-compose `v0.47.0`. Every
entry uses the deterministic characters-divided-by-four token proxy.

## Class inventories

* [Frontier seats](context-budget-role-seat-frontier-current.md) - Claude and
  Codex snapshots, eager totals, shared lazy totals, and composed counts.
* [Low-context seats](context-budget-role-seat-low-context-current.md) - Goose
  and OpenCode snapshots with optional skill sources removed.

Goose and OpenCode have equal token totals because each receives the same
catalog and AGENTS cascade. Their projection paths and payload hashes remain
distinct.

## Shared surface

* **AGENTS cascade** - Codex 10,079 eager tokens, Claude 10,241, Goose and
  OpenCode 9,872.
* **Frontier ordinary skills** - 807 eager and 13,857 lazy tokens across 13
  sources.
* **Low-context ordinary skills** - 699 eager and 10,799 lazy tokens across 11
  sources.
* **MCP** - zero eager schemas and 12 deferred server registrations.
* **Seat difference** - Claude adds 162 eager tokens over Codex through one
  additional AGENTS cascade component. Goose and OpenCode omit the two
  frontier-only ordinary sources and harness-specific AGENTS overrides.

## Cumulative tracked baseline

The checked-in ops/Codex baseline has a paired
[current snapshot](context-budget-ops-codex-current.yaml).

* **Eager** - fell from 14,564 to 13,823 tokens, a reduction of 741.
* **Lazy** - fell from 126,332 to 54,684 tokens, a reduction of 71,648.
* **Components** - added five, removed 30, and changed 25 across the full
  pruning interval.

## Interpretation

The AGENTS cascade is the dominant eager cost in every seat. Low-context
selection substantially cuts lazy retrieval and trims eager routing metadata,
but the inherited AGENTS surface keeps every OSS role above the legacy
5,000-token generic harness budget. Role-composed metadata ranges from a small
advisor set through the broad director catalog. Lazy totals describe available
retrieval, not startup prompt load.

## See also

* [Role-seat snapshot contract](context-budget-role-seat.md) - capture,
  comparison, and failure rules.
* [Historical ops/Codex baseline](context-budget-ops-codex-before.yaml) -
  machine-readable comparison source.
* [Context-budget report](context-budget.md) - component definitions and token
  proxy.

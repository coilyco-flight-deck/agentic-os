# Current role-class context inventory

The 11 canonical roles are measured in all four AOS native layouts. Claude and
Codex use the frontier catalog. Goose and OpenCode use the low-context catalog.
The snapshots were generated with released agent-compose `v0.47.0`. Every
entry uses the deterministic characters-divided-by-four token proxy.

## Roles

* [Director](context-budget-role-director-current.md) - frontier and low-context.
* [Engineer](context-budget-role-engineer-current.md) - frontier and low-context.
* [QA](context-budget-role-qa-current.md) - frontier and low-context.
* [Advisor](context-budget-role-advisor-current.md) - frontier and low-context.
* [Ops](context-budget-role-ops-current.md) - frontier and low-context.
* [PM](context-budget-role-pm-current.md) - frontier and low-context.
* [Designer](context-budget-role-designer-current.md) - frontier and low-context.
* [Social](context-budget-role-social-current.md) - frontier and low-context.
* [Community](context-budget-role-community-current.md) - frontier and
  low-context.
* [Sales](context-budget-role-sales-current.md) - frontier and low-context.
* [Customer success](context-budget-role-customer-success-current.md) -
  frontier and low-context.

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

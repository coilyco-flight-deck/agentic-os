# Current role-seat context inventory

This snapshot measures every canonical role in Claude and Codex at AOS commit
[`4bfa715`](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/commit/4bfa715).
It uses agent-compose 0.36.0 and the deterministic characters-divided-by-four
token proxy against this AOS checkout.

Each role reports Codex eager, Claude eager, shared lazy, then composed source
count. Lazy totals match across seats.

## Shared surface

* **AGENTS cascade** - Codex 10,079 eager tokens, Claude 10,241.
* **Ordinary skills** - 812 eager and 14,454 lazy tokens across 13 sources.
* **MCP** - zero eager schemas and 12 deferred server registrations.
* **Seat difference** - Claude adds 162 eager tokens through one additional
  AGENTS cascade component.

## Roles

* **Director** - [Codex 13,787](context-budget-director-codex-current.yaml), [Claude 13,949](context-budget-director-claude-current.yaml), lazy 89,123, 32 composed.
* **Engineer** - [Codex 13,172](context-budget-engineer-codex-current.yaml), [Claude 13,334](context-budget-engineer-claude-current.yaml), lazy 53,038, 23 composed.
* **QA** - [Codex 13,261](context-budget-qa-codex-current.yaml), [Claude 13,423](context-budget-qa-claude-current.yaml), lazy 47,121, 25 composed.
* **Advisor** - [Codex 12,094](context-budget-advisor-codex-current.yaml), [Claude 12,256](context-budget-advisor-claude-current.yaml), lazy 16,818, 2 composed.
* **Ops** - [Codex 13,343](context-budget-ops-codex-current.yaml), [Claude 13,505](context-budget-ops-claude-current.yaml), lazy 55,281, 26 composed.
* **PM** - [Codex 12,771](context-budget-pm-codex-current.yaml), [Claude 12,933](context-budget-pm-claude-current.yaml), lazy 52,473, 11 composed.
* **Designer** - [Codex 12,257](context-budget-designer-codex-current.yaml), [Claude 12,419](context-budget-designer-claude-current.yaml), lazy 24,160, 5 composed.
* **Social** - [Codex 12,308](context-budget-social-codex-current.yaml), [Claude 12,470](context-budget-social-claude-current.yaml), lazy 20,117, 5 composed.
* **Sales** - [Codex 12,229](context-budget-sales-codex-current.yaml), [Claude 12,391](context-budget-sales-claude-current.yaml), lazy 19,492, 4 composed.
* **Customer success** - [Codex 12,301](context-budget-customer-success-codex-current.yaml), [Claude 12,463](context-budget-customer-success-claude-current.yaml), lazy 19,594,
  4 composed.

## Latest pruning delta

The comparison point is the immediately preceding provider commit,
[`8489a02`](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/commit/8489a02).

* **Director, engineer, QA, and ops** - each shed 221 eager and 1,403 lazy
  tokens plus five composed sources.
* **Other six roles** - unchanged by the Azure, CloudFormation, GCP, Pulumi,
  and Ruby source deletion.
* **AGENTS follow-up** - later command-handover cleanup shed another 248 eager
  tokens from every seat.

## Cumulative tracked baseline

The checked-in ops/Codex baseline now has a paired
[current snapshot](context-budget-ops-codex-current.yaml).

* **Eager** - fell from 14,564 to 13,343 tokens, a reduction of 1,221.
* **Lazy** - fell from 126,332 to 55,281 tokens, a reduction of 71,051.
* **Components** - added five, removed 31, and changed 23 across the full
  pruning interval.

## Interpretation

The AGENTS cascade is now the dominant eager cost. Role-composed metadata ranges
from a small specialist set for advisor through the intentionally broad
director catalog. Lazy totals describe available retrieval, not startup prompt
load.

## See also

* [Role-seat snapshot contract](context-budget-role-seat.md) - capture,
  comparison, and failure rules.
* [Historical ops/Codex baseline](context-budget-ops-codex-before.yaml) -
  machine-readable comparison source.
* [Current ops/Codex snapshot](context-budget-ops-codex-current.yaml) -
  machine-readable post-pruning checkpoint.
* [Context-budget report](context-budget.md) - component definitions and token
  proxy.

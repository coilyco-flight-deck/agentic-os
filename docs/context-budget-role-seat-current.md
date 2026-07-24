# Current role-seat context inventory

This review snapshot measures every canonical role in the Claude and Codex
native seats at AOS commit
[`1529af7`](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/commit/1529af7).
It uses agent-compose 0.36.0 and the deterministic characters-divided-by-four
token proxy. The provider, repository, and CWD are this AOS checkout.

Each role line reports Codex eager, Claude eager, shared lazy, then the number
of role-composed sources. Lazy totals match across the two native seats.

## Shared surface

* **AGENTS cascade** - Codex 10,327 eager tokens, Claude 10,489.
* **Ordinary skills** - 751 eager and 13,764 lazy tokens across 12 sources.
* **MCP** - zero eager schemas and 12 deferred server registrations.
* **Seat difference** - Claude adds 162 eager tokens through one additional
  AGENTS cascade component.

## Roles

* **Director** - Codex 13,974, Claude 14,136, lazy 88,433, 32 composed.
* **Engineer** - Codex 13,359, Claude 13,521, lazy 52,348, 23 composed.
* **QA** - Codex 13,448, Claude 13,610, lazy 46,431, 25 composed.
* **Advisor** - Codex 12,281, Claude 12,443, lazy 16,128, 2 composed.
* **Ops** - Codex 13,530, Claude 13,692, lazy 54,591, 26 composed.
* **PM** - Codex 12,958, Claude 13,120, lazy 51,783, 11 composed.
* **Designer** - Codex 12,444, Claude 12,606, lazy 23,470, 5 composed.
* **Social** - Codex 12,495, Claude 12,657, lazy 19,427, 5 composed.
* **Sales** - Codex 12,416, Claude 12,578, lazy 18,802, 4 composed.
* **Customer success** - Codex 12,488, Claude 12,650, lazy 18,904,
  4 composed.

## Latest pruning delta

The comparison point is the immediately preceding provider commit,
[`8489a02`](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/commit/8489a02).

* **Director, engineer, QA, and ops** - each shed 221 eager and 1,403 lazy
  tokens plus five composed sources.
* **Other six roles** - unchanged by the Azure, CloudFormation, GCP, Pulumi,
  and Ruby source deletion.

## Cumulative tracked baseline

The checked-in ops/Codex baseline now has a paired
[current snapshot](context-budget-ops-codex-after.yaml).

* **Eager** - fell from 14,564 to 13,530 tokens, a reduction of 1,034.
* **Lazy** - fell from 126,332 to 54,591 tokens, a reduction of 71,741.
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
* [Current ops/Codex snapshot](context-budget-ops-codex-after.yaml) -
  machine-readable post-pruning checkpoint.
* [Context-budget report](context-budget.md) - component definitions and token
  proxy.

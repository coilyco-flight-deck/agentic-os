# Current role-seat context inventory

This review snapshot measures every canonical role in the Claude and Codex
native seats at AOS commit
[`8888cb2`](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/commit/8888cb29fbecdfad7c1c10c75cd1c37168f10757).
It uses agent-compose 0.30.0 and the deterministic characters-divided-by-four
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

* **Director** - Codex 14,035, Claude 14,197, lazy 89,624, 37 composed.
* **Engineer** - Codex 13,392, Claude 13,554, lazy 53,751, 28 composed.
* **QA** - Codex 13,478, Claude 13,640, lazy 47,834, 30 composed.
* **Advisor** - Codex 12,088, Claude 12,250, lazy 16,128, 2 composed.
* **Ops** - Codex 13,559, Claude 13,721, lazy 55,994, 31 composed.
* **PM** - Codex 12,799, Claude 12,961, lazy 51,571, 11 composed.
* **Designer** - Codex 12,248, Claude 12,410, lazy 23,470, 5 composed.
* **Social** - Codex 12,296, Claude 12,458, lazy 19,427, 5 composed.
* **Sales** - Codex 12,228, Claude 12,390, lazy 18,802, 4 composed.
* **Customer success** - Codex 12,294, Claude 12,456, lazy 18,904,
  4 composed.

## Latest pruning delta

The comparison point is the immediately preceding provider commit,
[`afb0b33`](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/commit/afb0b336e7b3b20e3570953f1c528d69d67e5fa6).

* **Director and PM** - each shed 131 eager and 22,734 lazy tokens while
  retaining `tooling-skill-authoring`.
* **Other eight roles** - each shed 175 eager and 35,078 lazy tokens.
* **Universal ordinary surface** - fell from 926 to 751 eager tokens and
  48,842 to 13,764 lazy tokens.
* **Warp** - fell from 4,416 to 317 lazy tokens and from six resources to zero.

## Interpretation

The AGENTS cascade is now the dominant eager cost. Role-composed metadata ranges
from a small specialist set for advisor through the intentionally broad
director catalog. Lazy totals describe available retrieval, not startup prompt
load.

## See also

* [Role-seat snapshot contract](context-budget-role-seat.md) - capture,
  comparison, and failure rules.
* [Context-budget report](context-budget.md) - component definitions and token
  proxy.

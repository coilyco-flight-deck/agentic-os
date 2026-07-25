# Role-orientation projections

AOS consumes public role orientation at authoring time while agent-compose
remains the canonical owner of roles, personalities, and seats. Shipped AOS
runtimes never fetch configuration from AOSH.

## Canonical source

Normal agent-compose convergence emits its complete structured person snapshot
at `~/.agent-compose/sources/personality/person.json`. The AOS personality sync
reads the `agent-compose.person-snapshot.v3` role order, ordered melds, and
canonical skill bindings directly. `--person-snapshot` accepts another emitted
artifact for isolated authoring and tests.

Purpose text, briefings, seats, identity primitives, model compatibility,
endpoints, hardware, permissions, and private routing are not copied into the
alignment board.

## Named seats

`ward exec sync-role-seats` projects each seat's harness, display name, and
pronouns into marker-bounded `agent` identity fields in
[`.ward/roles.kdl`](../.ward/roles.kdl). AOS continues to own surrounding
guardfiles, models, reasoning effort, and execution policy.

Every projected seat must already have a Ward agent block in that role. A new
harness therefore cannot silently become executable. Duplicate, malformed,
missing, or unconfigured seats fail closed.

## Personality alignment

`ward exec sync-role-personalities` writes
[`role-personalities.json`](../aos/role-personalities.json). The generated board
preserves every role's canonical order and ordered personality meld, then maps
each personality slug to its agent-compose `personality-*` skill id.

The board does not select runtime personality. Agent-compose continues to do
that from its embedded person source, which also owns the invariant and full
definitions.

## Context verification

Role-seat context capture reads the personality order and selected
`personality-*` skill ids from the actual agent-compose bundle. It compares
both with the generated AOS board before counting context. A missing, added,
reordered, or misbound personality fails closed. A successful snapshot records
the verified meld under `bundle.personalities`.

The seat's agent executable is still unnecessary. Agent-compose materializes
the configuration, while the measurement invokes no agent or model.

## Drift checks

Run `ward exec sync-role-seats -- --check` against the AOSH seat mirror. Run
`ward exec sync-role-personalities -- --check` after agent-compose convergence
for read-only personality verification. Local pre-commit visibly skips the
personality check when the generated snapshot is absent. A present but
malformed snapshot always fails.

## See also

* [Agent-compose AOS provider](personality-provider.md) - capability and behavioral boundary.
* [Role-seat context snapshots](context-budget-role-seat.md) - measured output contract.
* [AOSH projections](ward-local-models.md) - all authoring-time projection surfaces.

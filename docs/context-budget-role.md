# Role context snapshots

The context report measures one composed role. The role selects the complete
briefing, personality meld, and role-scoped skills. Harness, projection layout,
model route, model family, and context-window size are not inputs.

The command asks the local `agent-compose` binary to perform two operations:

* `roster` validates that the requested role exists.
* `compose` builds the role's complete `native-skills` bundle. AOS supplies the
  first role-supported tier from that roster only as Agent Compose compatibility
  metadata.

The measurement validates the bundle's ordered personality meld against the
person snapshot emitted by the same roster call, then reads the bundle directly.
It does not run Agent Compose's `project` operation. The command never invokes a
harness, agent, inference backend, model, hardware endpoint, or live service.

The AOS checkout is the default provider, repository, and CWD. `--provider`,
`--repo`, and `--cwd` make those inputs explicit for fixtures or reproduction.
Named multi-provider capture is part of the
[role capture workflow](context-budget-role-capture.md).

## Measurement boundary

The snapshot separates:

* **Eager context** - role instructions, the harness-neutral repository
  `AGENTS.md` root-to-CWD cascade, and ordinary, role, personality,
  role-composed, and optional plugin skill frontmatter.
* **Lazy context** - skill bodies and resources, optional plugin bodies and
  resources, and the count of deferred mcporter registrations.
* **MCP schemas** - zero eager schemas. The mcporter inventory contributes only
  a deferred registration count. The snapshot copies no configuration and
  queries no server.

The YAML artifact groups non-skill components and one top-level breakdown by
**eager** or **lazy** delivery and kind. Each skill appears once under `skills`
with its class, eager tokens, lazy tokens, and resource count. Stable ordering,
no timestamps, and no absolute source locators make identical inputs produce the
same payload hash.

Snapshots use `context-budget-<role>-<phase>.yaml`. AOS owns the reusable
measurement and validation contract. The consumer that determines the complete
provider combination owns its current snapshots and aggregate inventory.

## Capture and compare

The [role capture workflow](context-budget-role-capture.md) gives the
single-provider, multi-provider, and comparison commands plus their fail-closed
validation contract.

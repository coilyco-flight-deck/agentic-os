# Role-intent harness selection

AOS publishes a model-opaque default harness for every supported role-intent lane.
Harness selection answers which work surface receives a task. Backend model, server, score, fallback, and hardware selection remain separate concerns.

## Confirmed board

The committed board contains twelve roles and nineteen lanes:

* **engineer** - `autonomous-coding` uses `openhands`.
* **director** - `strategic-planning` uses `plandex`.
* **qa** - `code-review` uses `aider`.
* **advisor** - `research-synthesis` uses `hermes`.
* **ops** - `ops-investigation` uses `holmesgpt`. `operational-decision` uses `goose`.
* **pm** - `strategic-planning` uses `hermes`. `project-coordination` uses `plane`.
* **designer** - `product-shaping` uses `penpot`. `design-production` uses `aosx`.
* **social** - `message-composition` uses `mixpost`. `channel-publishing` uses `elizaos`.
* **community** - `knowledge-retrieval` uses `rasa`. `conversation-management` uses `elizaos`.
* **sales** - `research-synthesis` uses `hermes`. `conversation-management` uses `elizaos`.
* **customer-success** - `knowledge-retrieval` and `conversation-management` both use `rasa`.
* **ceo** - `strategic-planning` uses `hermes`.

Engineer is the sole unattended lane. Every role declares one or two intents,
and every lane has exactly one selected harness.

## Resolve a default

The released `aos` binary embeds the committed projection. Its resolver accepts
role identity at the control-plane boundary and emits only the selected harness
slug:

```bash
aos --role director harness-default --intent strategic-planning
```

The command prints `plandex`. A harness receives the selected intent through its
own adapter, never the role used to choose it.

Some selections are terminal agent harnesses. Others are product surfaces such
as Penpot, Plane, Mixpost, or Rasa. The resolver therefore does not auto-execute
its result. A launcher or Ward profile consumes the slug and invokes the
surface-specific adapter. `aos acompose` continues to require an explicit
container command:

```bash
aos --role engineer acompose -- codex
```

## Ownership and synchronization

AOS owns the public
[agent and harness capability registry](../.agents/harnesses.yaml), including
descriptions, source links, and compatible intents. AOSH owns its hand-selected
`roles.yaml` role-intent joins and `agent-selections.yaml` lane choices because
those inputs participate in hardware scoring and backend routing.

AOS also owns the generated `intent` children inside each canonical role in
[`.agents/roles.kdl`](../.agents/roles.kdl), the committed agent-compose
provider projection. Ward never parses these composition routes.

The sync also writes [`role-harnesses.json`](../aos/role-harnesses.json) as the
compiled view embedded by the standalone `aos` binary. The JSON does not become
a second hand-owned source. The drift check requires both generated views to
match the AOS capability registry joined with the same AOSH selection board.
Run `ward exec sync-harness-board` after the AOS registry or an AOSH selection changes. Run
`ward exec sync-harness-board -- --check` for a read-only drift check. Local
pre-commit performs the same check when the sibling AOSH checkout exists.
Public checkouts without that sibling report a visible skip.

The AOS registry is always required. Malformed or incomplete present AOSH
selection sources fail closed. Each generated KDL region is marker-bounded so
the sync preserves hand-owned composed-skill bindings.
The KDL carries role, intent, and harness identity. The JSON adds schema counts
and role-source provenance. Neither copies backend routing data.

## See also

* [AOS composed-container CLI](aos-cli.md) - released launcher behavior.
* [AOSH projections](ward-local-models.md) - authoring-time sync boundaries.
* [Role-composed skills](role-composed-skills.md) - role-scoped knowledge.

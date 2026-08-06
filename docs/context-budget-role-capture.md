# Role context capture

The role context report can capture one AOS bundle, combine named capability
providers, or compare a new bundle with a committed baseline. It invokes Agent
Compose but never projects to or launches a harness, agent, or model.

## Single provider

Capture the default AOS provider:

```sh
ward exec context-budget -- --role ops \
  --snapshot /tmp/context-budget-ops-current.yaml
```

## Multiple providers

Repeatable `--additional-provider ID=PATH` arguments admit other capability
providers into the same verified bundle:

```sh
ward exec context-budget -- --role ops \
  --additional-provider private-context=/path/to/provider \
  --snapshot /path/to/private/context-budget-ops-current.yaml
```

Agent Compose performs ordinary, role-composed, collision, and shadowing
decisions across the complete source set. The snapshot preserves each source id,
attributes selected skills to that provider, and records the provider identity
map without copying private source content into AOS.

## Compare

Copy the current snapshot to a task-scoped baseline, then capture and compare:

```sh
ward exec context-budget -- --role ops \
  --compare /tmp/context-budget-ops-baseline.yaml \
  --snapshot /tmp/context-budget-ops-current.yaml
```

`--skill-root` remains the separate input for plugin skills declared outside the
verified bundle. Duplicate skill ids, an unknown role, personality drift, an
unnamed or malformed provider, a wrong bundle role, or a mismatched comparison
subject fails closed.

## See also

* [Role context snapshots](context-budget-role.md) - measurement and artifact contract.
* [Context measurement](context-budget.md) - component definitions and token proxy.

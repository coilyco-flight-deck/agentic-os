# Skill model classes

AOS skill sources decide whether low-context models require their guidance.
Agent-compose enforces that source-owned decision while building a role bundle.

## Frontmatter

Ordinary `SKILL.md` and role-composed `COMPOSED.md` sources may declare one of:

```yaml
low-context: required
```

```yaml
low-context: optional
```

Missing metadata defaults to `required`. This preserves existing catalogs and
requires a positive authoring decision before agent-compose removes context.

## Decision rule

Classify each skill independently of its ordinary or role-composed placement.
Use `required` when the model needs the guidance to perform the work safely and
correctly. Use `optional` when the model is not expected to perform that work,
or when the source adds advanced technique without changing safe fundamentals.

Core Python guidance is required. High-end skill-authoring guidance is optional
for low-context models. Its director and PM role bindings remain unchanged.

## Composition

Agent-compose applies role admission first. Frontier requests keep the admitted
catalog. Low-context requests then exclude only explicitly optional sources.
Excluded sources appear in the selection trace and do not appear in the bundle
manifest or projected skill tree.

This metadata controls knowledge selection only. Ward continues to own command,
credential, mount, network, and runtime authority.

## See also

* [Agent-compose provider](personality-provider.md) - provider ownership.
* [Role-composed skills](role-composed-skills.md) - role admission.

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
AOS sets `require_low_context: true` in its skill catalog, so every ordinary
and role-composed source must publish an explicit decision.

## Decision rule

Classify each skill independently of its ordinary or role-composed placement.
Use `required` when the model needs the guidance to perform the work safely and
correctly. Use `optional` when the model is not expected to perform that work,
or when the source adds advanced technique without changing safe fundamentals.

Core Python guidance is required. High-end skill-authoring guidance is optional
for low-context models. Its director and PM role bindings remain unchanged.

Apply the rule by capability, not by source directory:

* **Required** - local truth, safety or authority boundaries, Kai's preferences,
  core implementation defaults, format and tool contracts, and the fundamental
  workflow that lets an admitted role perform its job correctly.
* **Optional** - frontier-only adapters, placeholder sources, high-end
  architecture or specialist methods, and long-horizon work a low-context
  model is not expected to perform.

The current provider has 71 explicit decisions. Optional sources are the
Claude-in-Chrome and agent-facing CLI adapters, the CloudFormation and Pulumi
stubs, Discord bot architecture, every `coding-shape-*` architecture umbrella,
causal-claim audit, cognitive walkthrough, product-signal triangulation,
product brainstorming, state-machine and visual QA methods, negotiation
architecture, all three scout methods, skill authoring, and system-improvement
vocabulary. Every other source is required.

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

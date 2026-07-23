# Agent-compose personality provider

AOS publishes the reusable personality bodies that agent-compose selects for
Kai's synthetic company. The provider is local and deterministic. A consumer
reads the checkout directly and fetches no context over the network.

## Ownership boundary

* **AOS** - owns the shared invariant plus full and brief role-neutral bodies.
* **agent-compose** - owns roles, compatibility, seats, names, pronouns, colors, and selection.
* **Ward** - owns executable authority, permissions, credentials, and runtime risk controls.

The shared slugs join the first two layers without moving authority into
personality content.

## Provider contract

Agent-compose infers one `personality-invariant` instruction and every
`personality-*` skill from the AOS root's `.agents/skills` directory. The
compose request supplies the stable source id `aos-public`, so adding a
personality body needs no parallel provider inventory.

Each personality directory carries two densities:

* `SKILL.md` - the full presence, attention, tempo, and voice definition.
* `BRIEF.md` - the same posture compressed into one short paragraph.

Agent-compose activates the complete ordered personality meld for a selected
role. A request cannot select an arbitrary trait or change compatibility.

## Local consumer use

An agent-compose request stored under the provider root admits that root:

```kdl
compose {
    role "engineer"
    delivery "native-skills"
    density "full"
    source "aos-public" root="." required=#true
}
```

`compiled` delivery uses `BRIEF.md` when the request asks for brief density
and `SKILL.md` for full density. Native delivery preserves the selected skill
directories. Both modes always carry the shared invariant as source
instructions.

Host convergence points `roster_sources` at the AOS checkout. The roster
artifact supplies seat dispatch and linked personality definitions to the
global cascade. Container composition uses the same provider to build one
immutable selected bundle.

## Behavioral boundary

Personality affects attention, framing, tempo, voice, and tie-breaking among
valid actions. Personality does not change truthfulness, uncertainty
reporting, obligations, acceptance criteria, permissions, safety,
escalation, rollback, or completion. A silent successful run needs no
personality theater.

## See also

* [Agents and sessions](features-agents-sessions.md) - host context composition.
* [Role surface tiers](role-surface-tiers.md) - the separate authority boundary.
* [docs/FEATURES.md](FEATURES.md) - shipped AOS capability inventory.

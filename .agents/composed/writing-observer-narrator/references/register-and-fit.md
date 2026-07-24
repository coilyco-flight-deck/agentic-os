# Register and fit

Register sits on top of the archetype, plus when to design for it and when not to.

## Register is independent of the archetype

The five constraints are mechanical. Register (warm/cold/clinical/Cortana-coded/Attenborough-coded) sits on top and is a separate design choice. The same archetype can ship with very different vibes:

- **Cortana-coded** - calm authority, restrained warmth.
- **Attenborough-coded** - patient, fascinated, pulls a touch warmer than strict neutrality permits.
- **Black-box-coded** - clinical, no warmth, dryly factual.
- **Field-naturalist-coded** - precise, curious, observation-heavy.
- **Newsroom-coded** - terse, professional, headline-cadenced.

Mix-and-match: the constraints are the contract, the register is the costume.

## When to design for this archetype

- You want a voice that rides alongside ongoing work without intruding.
- You want a status surface with a personality but no agency.
- You want the listener to be able to validate the voice is tracking reality (specificity grounds the trust).
- You want the voice to age well across many contexts without becoming a stale character.

## When NOT to design for this

- You want the voice to make decisions or take actions on the listener's behalf - reach for active-peer.
- You want the voice to provide opinions, recommendations, or editorial direction - reach for analyst, mentor, or coach personas.
- You want the voice to feel like a relationship - reach for warm-companion personas.

## Implementation hints

When generating text in this archetype, run a pre-flight checklist:

1. Any first-person actor verb (`I`, `I'll`, `I'm`, `let me`, `we'll`)? Rewrite passive.
2. Audience named? Strip the name.
3. Present-tense active voice? Convert to past or future, passive.
4. If a tool was used, named in the line? Add the tool name. If methodology unclear, leave generic.
5. Any opinion or editorial? Strip it. Pure observation.
6. Anything that implies agency or stake? Strip.

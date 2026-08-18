---
name: tooling-designer-temporal-brand
description: Apply or audit Temporal's visual system. Covers the three published brand colors, the named gradient set, the semantic token layer, Aeonik typography, scale, page architecture, and the workflow-state visual language. Triggers - Temporal brand, Temporal colors, ultraviolet, Space Black, Off White, Aeonik, Temporal UI, durable execution interface, workflow timeline visualization.
---

# Temporal brand system

Use this skill when designer applies Temporal's identity to a surface, audits an
interface against it, or borrows its structure for a system that has to make
long-running distributed state legible.

Exact values live in [`references/palette.md`](references/palette.md). Scale,
page shape, and the state-visualization language live in
[`references/architecture.md`](references/architecture.md). Read the reference
before quoting a number, because the published palette and the shipped token
layer are two different things.

## Activation boundary

Designer reads this skill as evidence about one external brand, not as a
default aesthetic. `kai-design-language` governs Kai's own surfaces and this
skill never overrides it. Turning a chosen direction into tokens, component
states, and contrast checks stays with `design-system`.

Reproducing Temporal's logo, wordmark, logomark, or licensed typeface is a
licensing question rather than a design one. Designer names the constraint and
hands it over instead of resolving it.

## Take the three published colors as fixed

Temporal publishes exactly three brand colors and nothing else.

* **UV** - `#444CE7` - rgb(68 76 231) - the sole brand accent, carrying brand surface, brand text, information state, and focus.
* **Space Black** - `#141414` - rgb(20 20 20) - the default page ground, a warm-neutral near-black rather than true black.
* **Off White** - `#F8FAFC` - rgb(248 250 252) - primary text on the dark ground and the inverse surface when a section flips light.

Every other value in the shipped site is a derived semantic token or a gradient
stop. Treat these three as immovable and everything downstream as the system
built on top of them.

## Read the ground as dark by default

The site sets its background surface to Space Black and its primary text to Off
White, then flips to an inverse surface for the sections that need to read as
paper. Light is the exception that gets declared, not the base that gets
overridden.

The neutral ramp between those poles is a desaturated blue-grey rather than a
grey, which is what keeps a near-black page from reading as dead. Borders,
table chrome, and secondary text all sit on that ramp.

## Carry the gradient set, not a gradient

Four gradients are named in Temporal's own SVG definitions, and each is a
two-stop linear ramp with no third color.

* **purple-ultraviolet** - `#B664FF` to `#444CE7` - the primary mark treatment, landing on the brand accent.
* **pink** - `#FF5555` to `#B664FF`
* **green** - `#C3FF62` to `#1FF1A5`
* **mist** - `#34D399` to `#FF6BFF`

These belong to marks, icon fills, and illustration. They are not page
backgrounds and they never sit under body text. A gradient here identifies a
thing, so it does not substitute for hierarchy.

## Set type in one family plus one mono

* **Aeonik** - the entire text face, from Air through Black, upright and italic. It is a geometric sans with mechanical construction and a wide weight range, which is what lets a single family carry both a 3.75rem hero and 0.75rem table chrome.
* **Aeonik Air** - shipped as its own family rather than a weight, so the hairline display cut has to be requested by name.
* **Noto Sans Mono** - code, event identifiers, and machine values.

Aeonik is a commercial release from CoType Foundry. Any reproduction needs its
own license, so designer names a substitute geometric sans when the license is
absent rather than shipping a lookalike silently.

## Make state legible before making it beautiful

Temporal's workflow views encode state in five separable channels, and each
channel answers exactly one question. Designer borrows the separation, not the
screenshots.

* **Dots** - a dot is one event. Position carries sequence.
* **Lines** - a line is a connection between events, and line weight distinguishes group from detail. A dashed line that animates forward means pending.
* **Icons** - an icon carries category alone, never status.
* **Colors** - color carries status first and category only as a secondary echo. Red is failure, dashed red is retrying, dashed purple is pending, green is completion.
* **Liveness** - the view updates in real time, and pending work is attached to the thing it belongs to rather than parked in a separate panel.

The discipline worth taking is the one-channel-one-question rule. When status
and category compete for the same channel, neither reads.

## Reject the near-misses

* Sampling a hex from a screenshot rather than the token layer, which produces a compressed approximation of a published value.
* Treating a campaign announcement banner color as brand, since that bar is content-driven and changes per campaign.
* Treating an embedded third-party widget's color as brand.
* Painting a surface with a mark gradient, which strands text on an unpredictable ground.
* Using true black instead of Space Black, which loses the warmth the palette depends on.
* Letting an icon carry status, which collapses the channel separation the state language rests on.

## Verify the result

* Confirm every color traces to a published brand color, a named gradient, or a semantic token, and name which one.
* Confirm status is readable without color alone, since the state language pairs color with line treatment and motion for exactly this reason.
* Check contrast on both the dark ground and the inverse surface, and check it across the full area of any gradient.
* Confirm the pending animation respects reduced-motion, because liveness is the one channel that is purely motion.
* Report a visual claim as unverified when no rendered evidence is available.

## Provenance

Extracted from [`temporal.io/brand`](https://temporal.io/brand), the shipped
site stylesheet, and
[the new-UI article](https://temporal.io/blog/the-dark-magic-of-workflow-exploration),
read in August 2026. Temporal owns these assets and this skill is a reading of
them, not a grant to use them. Re-read the sources before relying on a value,
since a shipped token layer moves without notice.

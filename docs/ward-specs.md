# Ward Spec Bundle

The aos-hosted deployment bundle for ward's coilyco build input lives directly
in [`.ward/`](../.ward/), flattened alongside `.ward/ward.yaml` (aos#330 - aos#315
first homed it at top-level `ward-specs/`). It carries the forgejo guardfile, the
signoz and ollama guardfiles, the fleet manifest, the smart-defaults bundle, and
the spec locks.

## Direction of truth: aos authors, ward consumes

**aos is the source of truth for the coilyco ward-specs bundle.** As of the
ward#503 producer cutover (Kai, 2026-07-07), the coilyco deployment values are
**authored here** and flow **down** into ward at release time, not the reverse.
This inverts the older shape, where ward's tree held the canonical values and aos
carried a lagging mirror that a `ward -> aos refresh` re-synced. Do **not**
reinstate it. When a coilyco fleet/guardfile/spec-lock value changes, change it
**here in aos's `.ward/`** and let a push republish the bundle. The launch
defaults stay spelled out here too: fleet `direct-main`, with only
`coilyco-flight-deck/ward` on `pull-requests-and-merge`. ward's tree
is being neutralized (ward#503 step 4), after which ward carries no coilyco
values and derives its whole shipped surface from this asset.

This is the one place a shipped tool (ward) consumes runtime config authored in a
reference repo (aos), a reasoned exception to AGENTS.md's config-placement
corollary. The bundle is Kai's single coilyco deployment, not fleet config every
ward user melds. External ward users build neutral and never fetch it. The
exception is stated in
[AGENTS.md](../AGENTS.md).

## Published as a pinned, checksummed release asset

Every aos release attaches the bundle as `ward-specs-<tag>.tar.gz` (plus a
`.sha256` sidecar) via the `release` job in
[`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml). The
tarball is deterministic, so the checksum a downstream pins is reproducible from
the tag. Ward's build sites pin that URL + `sha256` rather than a raw tracked
path, and the packaging step enumerates the bundle files explicitly so
`.ward/ward.yaml` never leaks into ward's overlay input.

## How ward consumes it

Both of ward's build sites - the brew formula and ward's release CI - **overlay
this published asset before the build**, re-deriving the shipped embeds from it.
During the staged cutover (ward#503) ward's tree still carries the coilyco
values as a fail-safe backstop, and this aos#332 work closes that gap: the
published bundle now reproduces ward's shipped surface byte-for-byte, so the
overlay is a **live no-op**.

This is the **assets-dir / release-asset overlay** convention, **not** a sibling
checkout. An earlier attempt wired ward's `make build-ward-kdl` to copy a sibling
`agentic-os/ward-specs/` working tree; ward reverted it because it broke
bare-clone builds and overlaid a stale copy.

The overlay mechanism on the ward side is decided (ward#503): each of ward's
build sites pins this asset by tag + `sha256`, verifies the checksum, extracts
it, and **copies the bundle's source guardfiles over ward's neutral tracked
tree before the build**. So the embeds are re-derived from this source bundle at
build time, with no pre-generated embeds committed in ward and no live spec
re-fetch or install-time generator.

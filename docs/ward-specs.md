# Ward Spec Bundle

The aos-hosted deployment bundle for ward's coilyco build input lives directly
in [`.ward/`](../.ward/), flattened alongside `.ward/ward.yaml` (aos#330 - aos#315
first homed it at top-level `ward-specs/`). It carries the forgejo guardfiles,
the raw Actions log bridge, the signoz and ollama guardfiles, the fleet
manifest, the smart-defaults bundle, and the spec locks.

## Direction of truth

**aos is the source of truth for the coilyco ward-specs bundle.** As of the
ward#503 producer cutover (Kai, 2026-07-07), the coilyco deployment values are
**authored here** and flow **down** into ward at release time, not the reverse.
This inverts the older shape, where ward's tree held the canonical values and aos
carried a lagging mirror that a `ward -> aos refresh` re-synced. Do **not**
reinstate it. When a coilyco fleet/guardfile/spec-lock value changes, change it
**here in aos's `.ward/`** and let a push republish the bundle. The launch
defaults stay spelled out here too: fleet `direct-to-main`, with
`coilyco-flight-deck/ward` and `coilyco-flight-deck/agentic-os` on
`pull-requests-and-merge`. ward's tree is being neutralized (ward#503 step 4),
after which ward carries no coilyco values and derives its whole shipped
surface from this asset.

This is the one place a shipped tool (ward) consumes runtime config authored in a
reference repo (aos), a reasoned exception to AGENTS.md's config-placement
corollary. The bundle is Kai's single coilyco deployment, not fleet config every
ward user melds. External ward users build neutral and never fetch it. The
Forgejo Actions log bridge stays here as a coilyco-specific overlay because the
upstream swagger omits the live web log route and the current renderer stays
JSON-first. The exception is stated in
[AGENTS.md](../AGENTS.md).

## Release asset

Every aos release attaches the bundle as `ward-specs-<tag>.tar.gz` (plus a
`.sha256` sidecar) via the `release` job in
[`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml). The
tarball is deterministic, so the checksum a downstream pins is reproducible from
the tag. Ward's build sites pin that URL + `sha256` rather than a raw tracked
path, and the packaging step enumerates the bundle files explicitly so
`.ward/ward.yaml` never leaks into ward's overlay input.

## How ward consumes it

ward now keeps one neutral shipped binary and selects the coilyco bundle at
launch through `WARD_CONFIG_REF` for the guarded edge surfaces. The former
release-time build overlay is gone, so the AOS asset is no longer a custom
binary input. The published `ward-specs-<tag>.tar.gz` remains the canonical
bundle artifact and checksum target, but the live config path is the runtime
`WARD_CONFIG_REF` seam, not a bespoke rebuild from the asset.

That keeps the coilyco deployment values authored here in `.ward/` and consumed
by ward without reintroducing the removed release overlay. The shell bootstrap
and dev-base image both stamp the ref from the checked-out commit, so the live
bundle follows the exact source tree that produced the container or shell
session. The current defaults bundle keeps `agentic-os` and ward itself on
`pull-requests-and-merge` under the `direct-main` fleet default.

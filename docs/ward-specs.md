# Ward Spec Bundle

The coilyco ward bundle lives in [`.ward/`](../.ward/), flattened beside
`.ward/ward.yaml`. It carries the Forgejo guardfiles, the Actions log and list
bridges, the rerun bridge, aws/tailscale/kubectl exec guardfiles, the agents
manifest, the role catalog, the workflow bundle, and the repos bundle. The
upstream Forgejo OpenAPI spec is no longer tracked as a committed blob in aos.

## Direction of truth

**aos is the source of truth for the coilyco ward-specs bundle.** Since the
ward#503 producer cutover (2026-07-07), coilyco deployment values are authored
here and flow down into ward at release time, not the reverse. This replaces
the older shape where ward held the canonical values and aos mirrored them.
When a coilyco fleet, guardfile, role-catalog, or spec-lock value changes,
change it here in aos's `.ward/` and let a push republish the bundle. The
launch defaults stay spelled out here too: fleet `merge-remote-main`, with
cli-guard, ward, and agentic-os on `pull-request-and-merge` (canonical
ward#508 spellings).

This is the one place a shipped tool (ward) consumes runtime config authored in
a reference repo (aos), a deliberate exception to AGENTS.md's config-placement
corollary. The bundle is Kai's single coilyco deployment, not fleet config
every ward user melds. Forgejo splits into a compatibility monolith for the
current `ward ops forgejo` runtime surface plus role-facing read, write, and
admin tier guardfiles. The raw Actions log bridge, list bridge, and rerun
bridge stay here as coilyco-specific overlays because the upstream swagger
omits the live log, list, and rerun routes and the current renderer stays
JSON-first. The exception is stated in [AGENTS.md](../AGENTS.md).

See [ward-specs-overrides.md](ward-specs-overrides.md) for the agent overlay.

## Profile asset home

When Ward consumes typed profile data, AOS owns the surviving profile and
config assets under [ward-profile-assets.md](ward-profile-assets.md).

## Release asset

Every aos release attaches the bundle as `ward-specs-<tag>.tar.gz` (plus a
`.sha256` sidecar) via the `release` job in
[`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml). The
tarball is deterministic, so the checksum a downstream pins is reproducible from
the tag. Ward's build sites pin that URL + `sha256` rather than a raw tracked
path, and the packaging step enumerates the bundle files explicitly while
keeping `.ward/ward.yaml` out of the tarball, so new bundle files land only
when the release list is updated and the overlay input stays clean.

## How ward consumes it

ward keeps one neutral shipped binary and selects the coilyco bundle at launch
through `WARD_CONFIG_REF` for the guarded edge surfaces. The published
`ward-specs-<tag>.tar.gz` remains the canonical bundle artifact and checksum
target, but the live config path is the runtime `WARD_CONFIG_REF` seam, not a
bespoke rebuild from the asset.

Landing policy lives in [`.ward/workflow.kdl`](../.ward/workflow.kdl). Its
`workflow` block keeps the coilyco PR-gated repos explicit.

Host shells and the container entrypoint point `WARD_CONFIG_REF` at the
checkout's `.ward/` live (`file://`): no commit pin to rot in a long-lived
terminal, no gitsync or git credential at launch (the stale-pin fail-closed
chain behind aos#452/aos#472). Only the dev-base image build bakes a
commit-pinned ref, the fallback without a seeded checkout.

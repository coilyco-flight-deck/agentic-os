# Ward Spec Bundle

The coilyco ward bundle lives in [`.ward/`](../.ward/), flattened beside
`.ward/ward.yaml` (aos#330, first homed at top-level `ward-specs/`). It carries
the Forgejo guardfiles, the Actions log bridge, AWS and kubectl guardfiles, the
agents manifest, the role catalog, the defaults bundle, and the repos bundle.
The upstream Forgejo OpenAPI spec is no longer tracked as a committed blob in
aos.

## Direction Of Truth

**aos is the source of truth for the coilyco ward-specs bundle.** The coilyco
deployment values are authored here and flow down into ward at release time.
Do not restore the older mirror shape where ward was canonical and aos was a
refresh target. Change fleet, guardfile, role-catalog, or spec-input boundary
values here in `.ward/` and republish. The launch defaults stay
`direct-to-main`, with `coilyco-flight-deck/ward` and
`coilyco-flight-deck/agentic-os` on `pull-requests-and-merge`.

This is the one place a shipped tool (ward) consumes runtime config authored in
a reference repo (aos), a reasoned exception to AGENTS.md's config-placement
corollary. The bundle is Kai's single coilyco deployment, not fleet config
every ward user melds. For Forgejo, the read tier owns the shared spec URL,
base URL, auth, explicit read grants, and inherited denials. The write tier
inherits read and adds authoring verbs. The admin tier inherits write and adds
targeted delete verbs. Role guardfile bindings live in `.ward/roles.kdl` as
repeated singular `guardfile` nodes. When no embedded lock is present, ward
fetches the upstream Forgejo OpenAPI from the configured URL. That keeps the
guardfiles deterministic by URL without committing the 810K blob.
`WARD_KDL_OPS_FORGEJO_SPEC` can still point at a locally generated cache if an
operator wants to override the live fetch. The raw Actions log bridge stays
here as a coilyco-specific overlay because the upstream swagger omits the live
web log route and the current renderer stays JSON-first. The exception is
stated in [AGENTS.md](../AGENTS.md).

## Release Asset

Every aos release attaches `ward-specs-<tag>.tar.gz` plus a `.sha256` sidecar
via the `release` job in [`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml).
The tarball is deterministic, so downstream checksums stay reproducible from
the tag. The packaging step enumerates the bundle files explicitly so
`.ward/ward.yaml` never leaks into ward's overlay input.

## How Ward Consumes It

ward keeps one neutral shipped binary and launches the coilyco bundle through
`WARD_CONFIG_REF`. The former release-time build overlay is gone, so the AOS
asset is no longer a custom binary input. The published
`ward-specs-<tag>.tar.gz` remains the canonical bundle artifact and checksum
target, but the live config path is the runtime `WARD_CONFIG_REF` seam, not a
bespoke rebuild from the asset. When the Forgejo lockfile is absent, ward
resolves the upstream spec from the configured Forgejo swagger URL and tells
the operator to run `kdl-specs lock` if a cached input is desired.

The shell bootstrap and dev-base image stamp the ref from the checked-out
commit, so the live bundle follows the source tree that produced the container
or shell session. The current defaults bundle keeps `agentic-os` and ward
itself on `pull-requests-and-merge` under the `direct-main` fleet default.

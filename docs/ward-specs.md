# Ward Spec Bundle

The aos-hosted deployment bundle for ward's coilyco build input lives directly
in [`.ward/`](../.ward/), flattened alongside `.ward/ward.yaml` (aos#330 - aos#315
first homed it at top-level `ward-specs/`). It carries the forgejo guardfile, the
signoz and ollama guardfiles, the fleet manifest, and the spec locks the ward
build consumes.

## Published as a pinned, checksummed release asset

Every aos release attaches the bundle as `ward-specs-<tag>.tar.gz` (plus a
`.sha256` sidecar) via the `release` job in
[`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml). The
tarball is deterministic (sorted entries, zeroed mtime/owner, `gzip -n`), so the
checksum a downstream pins is reproducible from the tag. Ward's build sites pin
that URL + `sha256` rather than a raw tracked path, giving them a stable,
verifiable input. The packaging step enumerates the bundle files explicitly (not
a whole-directory tar) so `.ward/ward.yaml` never leaks into ward's overlay input,
while the tarball's internal entries stay flat and layout-identical to the
pre-move asset - so ward#503's overlay extract needs no change.

## How ward consumes it

Ward's own tracked build input still carries the coilyco values today. The
cross-repo plan (ward#503) is to neutralize ward's tree and have both of ward's
build sites - the brew formula and ward's release CI - **overlay this published
asset before the build**, so ward's default bundle can go deployment-agnostic
without breaking the fleet's brew-from-source install.

This is the **assets-dir / release-asset overlay** convention, **not** a sibling
checkout. An earlier attempt wired ward's `make build-ward-kdl` to copy a sibling
`agentic-os/ward-specs/` working tree; ward reverted it (the commit dropping the
`WARD_SPEC_BUNDLE_DIR` overlay) because it broke bare-clone builds and overlaid a
stale copy. The bundle travels as a pinned release asset instead.

The overlay mechanism on the ward side is decided (ward#503): each of ward's
build sites pins this asset by tag + `sha256`, verifies the checksum, extracts
it, and **copies the bundle's source guardfiles over ward's neutral tracked
tree before the build** - the same file-copy `make sync-*-assets` uses to derive
ward's committed embeds. So the embeds are re-derived from this source bundle at
build time (no pre-generated embeds committed in ward, no live spec re-fetch or
install-time generator). This asset is the pinned source of truth.

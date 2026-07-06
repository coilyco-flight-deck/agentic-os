# Ward Spec Bundle

`ward-specs/` is the aos-hosted deployment bundle for ward's coilyco build
input. It carries the forgejo guardfile, the signoz and ollama guardfiles, the
fleet manifest, and the spec locks the ward build consumes (aos#315).

## Published as a pinned, checksummed release asset

Every aos release attaches the bundle as `ward-specs-<tag>.tar.gz` (plus a
`.sha256` sidecar) via the `release` job in
[`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml). The
tarball is deterministic (sorted entries, zeroed mtime/owner, `gzip -n`), so the
checksum a downstream pins is reproducible from the tag. Ward's build sites pin
that URL + `sha256` rather than a raw tracked path, giving them a stable,
verifiable input.

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

The exact overlay mechanism on the ward side - whether the build regenerates the
embedded guardfiles from this source bundle at build time, or ward ships
pre-generated embeds that the asset overlays directly - is the open decision
tracked in ward#503. Either way this asset is the pinned source of truth.

See [../ward-specs/README.md](../ward-specs/README.md).

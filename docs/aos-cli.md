---
doc_goal: Define the standalone AOS container launcher, its workspace and substrate contract, and the deferred release shape.
---
# AOS composed-container CLI

`aos` launches the dev-base image without Ward:

```bash
aos --role engineer acompose -- codex
```

The command after `--` is preserved exactly. Its executable selects the
agent-compose layout unless `--layout` names one explicitly. `--role`,
`--density`, and `--delivery` become a normal agent-compose request.

## Launch contract

Every launch supplies the same runtime base:

* CWD mounts read-write at `/workspace/<cwd-name>` and becomes the workdir.
* `aos-substrate-cache` mounts at `/var/cache/aos/git`.
* The image manifest hydrates fresh reference trees under
  `/substrate/<owner>/<repo>`.
* The selected harness's known auth file mounts read-only when present. AOS
  copies it into the ephemeral HOME before dropping privileges.
* Present API-key environment variables cross by name, never by rendered value.
* The Docker socket, AWS config, host HOME, and Git credentials do not mount.

Root performs bootstrap only. The harness runs as the host uid and gid with an
ephemeral `/home/aos`, keeping a Linux bind-mounted workspace writable while
the root-owned substrate stays read-only.

## Composition flow

The image carries `agent-compose`, its `acompose` alias, and the AOS provider
snapshot inside the baked AOS substrate seed. Container bootstrap:

1. refreshes the shared mirrors from the image seeds without network
2. materializes the reference checkouts
3. composes the requested role
4. verifies the immutable bundle
5. projects it with `project --scope home`
6. execs the command after `--`

`--no-substrate` omits general reference trees but still materializes the AOS
provider required for composition. The runtime invokes no Ward command,
config, bootstrap, authority, or lifecycle.

## Ownership

AOS owns the reusable runtime substrate: image seeds, public roster, CWD
mount, cache hydration, workspace and reference topology, and composed HOME.
Ward owns governed execution layered above it: fresh target clones, writable
repo grants, credential scopes, issues, reservations, reaping, and landing.
Ward can later consume this primitive without moving those policies into AOS.

## Release specification

The CLI will copy agent-compose's Forgejo-canonical release shape:

* every main push validates, then queues an automatic minor release
* manual dispatch retries a tag or selects patch, minor, or major
* builds publish `aos-darwin-arm64`, `aos-linux-amd64`,
  `aos-linux-arm64`, and `aos-windows-amd64.exe`
* `SHA256SUMS`, `aos.rb`, and `aos.json` ship beside the binaries
* the Homebrew tap and Scoop bucket update from generated metadata
* `aos version` reports the stamped tag

This release automation is specified, not implemented, in the first launcher
slice. Local development uses `ward exec aos-build`, `aos-test`, `aos-lint`,
`aos-install`, and the focused image/smoke verbs.

## See also

* [dev-base-image.md](dev-base-image.md) - image tiers and publication.
* [personality-provider.md](personality-provider.md) - composed source.
* [FEATURES.md](FEATURES.md) - shipped inventory.

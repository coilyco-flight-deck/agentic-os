---
doc_goal: Define AOS as the composition root for independent role context, guarded tools, and Ward-governed container launches.
---
# AOS launch CLI

AOS exposes one launch shape for three independently useful capabilities:

```bash
aos \
  --agent codex \
  --role engineer \
  --warded \
  --composed \
  --guarded \
  -- owner/repo#267
```

The shared role slug is a selection protocol. Agent-compose uses it to choose
context. Ward uses it to choose Ward-owned policy. A matching name never
transfers permissions or unions authority between the tools.

## Capability flags

* `--warded` - AOS invokes the host Ward CLI with the selected agent, role,
  image, workspace request, and optional generic context bundle. Ward remains
  the Docker Compose, broker, credential, lifecycle, and teardown owner.
* `--composed` - AOS asks agent-compose to verify and project the selected role
  into a private staged home.
* `--guarded` - AOS attaches the AOS-specific `aosguard` binary and its
  specgen-generated native skill.

The flags remain separate. `--warded` alone uses Ward's embedded default role
context. `--warded --composed` adds composed context. `--warded --guarded`
adds the guarded tool and generated skill without asking agent-compose to
compose a role. All three flags enable the full launch.

Without `--warded`, AOS owns one standalone container. Arguments after `--`
become arguments to the selected agent:

```bash
aos --agent codex --role engineer --composed -- --version
aos --agent codex --role engineer --guarded
```

The existing explicit command stays available and keeps its original exact
command forwarding:

```bash
aos --role engineer acompose -- codex
```

## Warded handoff

Ward accepts one narrow, provider-neutral bundle:

```text
context-bundle.json
home/<selected instruction and skill roots>
bin/aosguard
```

AOS uses the selected AOS image as a short-lived materializer. It verifies the
agent-compose bundle, projects an empty staged home, removes
`.agent-compose/` bookkeeping, validates that only the selected load points
remain, and adds guarded assets when requested. AOS writes Ward's strict
`ward.context-bundle.v1` manifest only after those checks pass.

Materialized bundles are content-addressed and immutable under the user's AOS
cache. They persist because a detached Ward run can outlive the host `aos`
process. Ward validates the bundle before Docker starts, mounts it read-only,
revalidates it during bootstrap, and appends Ward-owned authority context
inside the private agent home.

AOS checks the known role and agent matrix, rejects translated Ward flags in
the forwarded arguments, confirms the installed Ward advertises the generic
bundle contract, and fails unsupported combinations before starting the
materializer.

Ward ships `director`, `qa`, and `engineer`. Other agent-compose roles remain
available on the standalone composed path.

## Standalone container contract

Every standalone launch supplies the same runtime base:

* CWD mounts read-write at `/workspace/<cwd-name>` and becomes the workdir.
* `aos-substrate-cache` mounts at `/var/cache/aos/git` when composition needs
  the baked provider.
* AOS copies the selected harness's read-only auth into the ephemeral HOME.
* Codex trusts the exact workspace, skips inner approvals, uses its full-access
  inner sandbox, defaults to Terra-medium, and hides rate-limit model nudges.
* Present API-key environment variables cross by name, never by rendered value.
* The Docker socket, AWS config, host HOME, and Git credentials do not mount.

Root performs bootstrap only. The harness runs as the host uid and gid with an
ephemeral `/home/aos`.

## Composition flow

The image carries self-contained `agent-compose`, its `acompose` alias, and the
AOS capability provider inside the baked substrate seed. Standalone composed
bootstrap:

1. refreshes the shared mirrors and materializes reference checkouts
2. composes the requested role for the selected layout's model class
3. verifies the immutable bundle
4. projects it with `project --scope home` and execs the selected harness

`--no-substrate` omits general reference trees but still materializes the AOS
capability provider required by a composed request. Personality context stays
inside agent-compose.

## Validation

```bash
ward exec aos-build
ward exec aos-test
ward exec aos-composition-dry-run -- owner/repo#267 --print
ward exec aos-image-build
ward exec aos-designer-smoke
```

The designer smoke verifies role instructions, skill promotion, no host auth
or unrelated substrate, and role isolation.

## Ownership

AOS is the only composition layer aware of all three sibling capabilities. It
owns translation, staged-home materialization, guarded asset assembly, and the
public flag matrix.

Agent-compose remains an independent context producer. cli-guard and specgen
remain an independent guarded-tool generator. Ward remains an independent
governed runtime and the only authority owner in warded mode.

The cross-repository contract is tracked in
[inbox#267](https://forgejo.coilysiren.me/coilysiren/inbox/issues/267). The AOS
implementation is tracked in
[agentic-os#755](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/755).

## Release

The [CLI release pipeline](aos-cli-release.md) validates every main push and
publishes the next minor `aos-v*` release. It cross-compiles checksummed
binaries, renders Homebrew and Scoop metadata, and stamps `aos version`.

## See also

* [aosguard.md](aosguard.md) - AOS-specific guarded tool and generated skill.
* [dev-base-image.md](dev-base-image.md) - full image contents and publication.
* [aos-cli-release.md](aos-cli-release.md) - binary and package delivery.
* [personality-provider.md](personality-provider.md) - composed source.
* [FEATURES.md](FEATURES.md) - shipped inventory.

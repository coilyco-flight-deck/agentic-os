# aosguard

`aosguard` is AOS's guarded operator CLI. The name is intentionally
AOS-specific. cli-guard and specgen remain generic products, while AOS owns
this concrete policy snapshot, release name, and launch integration.

Packaged `specgen` discovers the [`.specgen/`](../.specgen/README.md) project,
materializes generated Go out of band, and emits the `aosguard` binary without
committed Go build glue. The full dev-base image and native AOS releases build
from the same source and lock. Homebrew and Scoop install it beside `aos`.

## Authority boundary

The snapshot carries operator-facing Forgejo, AWS, kubectl, Tailscale, combined
Actions bridge, and runner-token fetch leaves. The Actions bridge lives at
`aosguard ops actions` so its exec transport does not shadow the spec-backed
`aosguard ops forgejo` group. The snapshot excludes Ward's role-scoped agent
policy. Forgejo metadata includes `repo-topic replace-all <owner> <repo>`,
whose repeated `--topics` values become the repository's complete topic set.

Ward selects role policy dynamically. Specgen merges every member with the same
`wrap` identity into one static binary. Copying every Ward role source into
`aosguard` would silently union role authority, so the two policies stay
separate.

## Generated skill

Specgen renders one concise native skill plus a complete lazy command index:

```text
aosguard/SKILL.md
aosguard/references/commands.yaml
```

The full image builds those files beside the binary. `aos --guarded` projects
the skill into the selected agent's skill root. In warded mode, AOS also puts
the binary under the generic bundle's `bin/` directory. Ward mounts it
read-only after the image's PATH, so it cannot shadow an image tool.

The skill grants no permission. The running `aosguard --help`, nested group
help, and `describe` surfaces remain authoritative.

## Source ownership

`.specgen/aosguard/` owns the operator policy. `.ward/` owns the role-scoped
Ward bundle described in [ward specs](ward-specs.md). Neither tree is generated
from the other, and no drift check forces them to match. A policy that agents
and operators both need is reviewed in both authority contexts.

The Forgejo source is vendored from the pruned deployment contract, so
`aosguard-lock` refreshes the dependency graph without reaching a live Forgejo
edge. The source Swagger remains plain JSON for review, while its generated API
lock is deterministic gzip at `forgejo.swagger.lock.json.gz`. Specgen decodes
that lock before use. The resulting `specverb.lock` pins cli-guard for
reproducible builds.

Specgen no longer emits per-member Markdown. `aosguard-lock` instead refreshes
the native skill under ignored `dist/skills/`, while maintained product
documentation stays under `docs/`.

## Development

`ward exec aosguard-build` materializes `dist/aosguard` and refreshes the
generated skill. `ward exec aosguard-run --` passes subsequent arguments to the
generated command. `ward exec aosguard-lock` is the only lock-writing step and
uses the packaged `specgen` executable.

Actions leaves call packaged `agentic_os` Python modules. Native `aosguard`
releases embed the same bridge, so every leaf works outside a source checkout.

Cross-repository composition is tracked in
[inbox#267](https://forgejo.coilysiren.me/coilysiren/inbox/issues/267). The AOS
implementation is tracked in
[agentic-os#755](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/755).

## See also

* [AOS launch CLI](aos-cli.md)
* [Feature inventory](FEATURES.md)
* [Ward bundle](ward-specs.md)

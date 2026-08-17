# aosguard

`aosguard` is AOS's guarded operator CLI. umbra and specgen remain generic,
while AOS owns this concrete policy snapshot, release name, and integration.

Packaged `specgen` discovers the [guardfile project](../.specgen/README.md),
materializes generated Go out of band, and emits `aosguard` without committed
Go build glue. Dev-base and native AOS releases build from the same source and
lock. Homebrew and Scoop install it beside `aos`.

## Authority boundary

The snapshot carries Forgejo, AWS, kubectl, Tailscale, Actions, SigNoz, and
runner-token leaves, and excludes Ward role policy. AWS SSM permits single
reads, file-backed writes, and named deletions. Actions lives at `aosguard ops
actions` so its exec transport does not shadow `aosguard ops forgejo`. The
sibling [`forgejo-storage measure` bridge](forgejo-ops.md) uses fixed `kubectl
exec` operations from an embedded script invoked by absolute path. `aosguard
ops signoz` reads only the converged SigNoz MCP server.

Forgejo pin actions are fixed to a single tracker where coilyco-ops holds
admin. Both wrappers read their credential from SSM through the same `provider
ssm` shape, so it never enters argv, logs, or tracked files.

Ward's fixed broker and AOSguard's static operator surface are independent, and
neither imports role-derived grants from the other.

## Generated skill

Specgen renders one concise native skill, `aosguard/SKILL.md`, plus a complete
lazy command index at `aosguard/references/commands.yaml`.

The full image builds those beside the binary and `aos --guarded` projects the
skill into the selected agent's skill root. In warded mode AOS also puts the
binary under the generic bundle's `bin/`, which Ward mounts read-only after the
image's PATH so it cannot shadow an image tool. The skill grants no permission:
`aosguard --help`, nested group help, and `describe` stay authoritative.

## Source ownership

`.specgen/guardfiles/aosguard/` owns the operator policy, vendored Swagger
inputs, and generated API locks. Ward owns its broker internally. Neither
product reads policy from the other, and no drift check forces them to match.

The Forgejo source is vendored from the pruned deployment contract, so
`aosguard-lock` refreshes the dependency graph without reaching a live Forgejo
edge. Swagger and its generated lock use deterministic gzip and specgen decodes
each before use, and the resulting `specverb.lock` pins umbra for reproducible
builds. `aosguard-lock` refreshes the native skill under ignored
`dist/skills/`, while maintained documentation stays under `docs/`.

## Development

`ward exec aosguard-build` materializes `dist/aosguard` and refreshes the
generated skill. `ward exec aosguard-run --` passes subsequent arguments to the
generated command. `ward exec aosguard-lock` is the only lock-writing step and
uses the packaged `specgen` executable.

Cross-repository composition is tracked on the intake tracker, with AOS
implementation in [agentic-os#755](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/755).

## The Forgejo admin wrapper

`forgejo-admin` holds repo settings and cosmetics, org labels, repo topics, and
branch protection. Forgejo refuses every one of them to `coilyco-ops`, an org
member holding push rather than an owner holding repo-admin, so the credential
is already a sufficient gate. Narrowing each action to its safest field on top
of that cost more than it bought, so `repo edit` exposes the whole
`EditRepoOption`, the same field set
`infrastructure/scripts/forgejo-repo-settings.py` converges.

`private` and `archived` ride along rather than being blocked, because anyone
who can reach this wrapper can already flip either in the UI in fewer steps.

Deletes stay marked: `org-label delete` strips the label from every issue
carrying it, so the guardfile names `edit org-label` as the rename path, which
keeps the label id and every association. Org-label writes on the ordinary
wrapper are `never` leaves naming the admin verb, rather than the bare
`403 Must be an organization owner` they used to answer.

## What it covers

Repo settings and cosmetics, org labels, topics, branch protection, Actions
secrets for repos and orgs, runner registration tokens, package retention,
repository contents, and the bot's personal access tokens.

The surface grew because provisioning scripts were reading the PAT into a shell
variable and passing it to `curl`. A guarded verb keeps the credential inside
the binary, so it never reaches a variable, a log, or `ps`. That is the point of
the wrapper, and a script that fetches the token itself defeats it however
carefully it handles it afterwards.

Two entries are credential-shaped rather than config-shaped and are worth
reading twice. `user-token create` returns the only copy of a new PAT, so its
stdout is the secret. `package delete` and `user-token delete` are irreversible.

## What it does not do, deliberately

It does not create or delete Forgejo users, and it does not create
organizations. Those are `never` leaves carrying the reason, so the boundary is
executable rather than a convention someone has to remember.

The line is that aosguard operates the estate and does not create principals in
it. A guard that can mint a user can mint one with any rights, which makes every
other restriction on the wrapper decorative. Kai's call, 2026-08-16.

The two bootstrap scripts that need those operations -
`provision-coilyco-ops-bot.sh` and `grant-coilyco-ops-org-repo-create.sh` in
`coilyco-flight-deck/infrastructure` - keep reading `/forgejo/admin-token` from
SSM directly. They run approximately once, so the standing capability a verb
would create costs more than the direct read.

## Credentials

The PAT comes from `/forgejo/admin-token` through the same `provider ssm` block
the ordinary wrapper uses, resolved at call time. There is no environment
variable to export and no wrapper script to run first. Access to the parameter
is the boundary, which is where an SSM-backed credential's boundary belongs.

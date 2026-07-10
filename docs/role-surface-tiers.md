# Role surface tiers

The intended capability surface each `ward agent` container role carries, made
deliberate after the 2026-07-10 permissions rollback stripped the director and
advisor surfaces below operational need (agentic-os#447, probed live during the
infrastructure#538 recovery). This is the reviewed definition. A live surface
that differs from it is drift to fix.

## Tiers

* **engineer** - forgejo read + actions read + write - lands code inside its clone, no live infra reach.
* **qa** - forgejo read + actions read + write - inspects a candidate and posts a verdict comment.
* **advisor** - forgejo read + actions read + aws/ssm + tailnet live-observe - answers with live findings, never writes code. The live-observe pair (tailnet + `~/.aws`) is the documented default this role lost in the rollback.
* **director** - forgejo read + actions read + write + aws/ssm + kubectl + runner-token mint + tailnet live-observe - drives the headless lane and fronts incident recovery.
* **ops** - forgejo read + actions read + write + aws/ssm + kubectl + runner-token mint + tailnet live-observe - live system maintenance, the widest tier.

Runner-token mint is `ward ops forgejo actions generate-runner-token`
([guardfile](../.ward/guardfile.forgejo.runnertoken.kdl)), restored because its
absence blocked the infrastructure#539 token restore. It stays out of the
fleet-wide [readactions overlay](../.ward/guardfile.forgejo.readactions.kdl):
minting a registration credential is director/ops reach, not a read.

## Layer ownership

Each capability is owned by exactly one layer. Name the layer when changing a
role's reach, so a one-layer rollback reads as drift against this map instead
of silently disabling a role.

* **guardfile bindings** - [.ward/roles.kdl](../.ward/roles.kdl), authored here - which guarded verb families a role mounts: the forgejo read/readactions/write tiers, [aws](../.ward/guardfile.aws.kdl), [kubectl](../.ward/guardfile.kubectl.kdl), [runner-token](../.ward/guardfile.forgejo.runnertoken.kdl).
* **role presets** - ward's tree - tagline, capabilities, modes, posture. Stripped from the aos overlay on 2026-07-10 (commit 566f42f) by design, never re-authored here.
* **image binaries** - [docker/dev-base/](dev-base-image-tiering.md), authored here - whether `aws`, `kubectl`, `helm`, `tailscale`, and the Docker client exist on disk. They land in the `ops` image tier and flow into `agent` and `full`.
* **container bring-up** - ward's tree - whether creds and daemons are live: the `~/.aws` dir, a kubeconfig, `tailscaled` up and authed, `FORGEJO_TOKEN`, and the `WARD_CONTEXT_LEVEL` context slice. A binary existing says nothing about this layer.

The 2026-07-10 incident was a bring-up-layer rollback: the guardfiles still
compiled in, but the binaries, creds, and daemons under them were gone, and
nothing flagged it.

## The self-check

[.ward/surface-check.sh](../.ward/surface-check.sh) asserts a live surface
matches its role's tier (`$WARD_ROLE`, or pass the role as the first argument).
It probes each promise above - binaries on PATH, creds present, `tailscale
status` answering, kubeconfig readable, the runner-token verb mounted - and
exits non-zero listing every miss, so an over-broad rollback fails loud at
bring-up, not by hand mid-incident. Run it as `ward exec surface-check`. It
rides the ward-specs bundle. Wiring it into ward's bring-up path is ward-side
work, filed as a follow-up from agentic-os#447.

## Deferred

Merge authority and commit-status read stay out of this map on purpose. The
ward-native PR workflow capability is foundational ward-side work, and the
specgen also-grant convenience is agentic-os#446. Neither is duplicated here.

## See also

* [ward-specs.md](ward-specs.md) - the bundle these guardfiles ship in.
* [dev-base-image-tiering.md](dev-base-image-tiering.md) - the image tier split.
* [ward-ops-forgejo-reference.md](ward-ops-forgejo-reference.md) - the committed forgejo surface render.

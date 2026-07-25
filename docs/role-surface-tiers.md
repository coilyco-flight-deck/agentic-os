# Role surface tiers

The intended capability surface each `ward agent` container role carries, made
deliberate after the 2026-07-10 permissions rollback stripped the live-observe
surfaces below operational need (agentic-os#447). This is the reviewed
definition. A live surface that differs from it is drift to fix.

## Tiers

* **engineer** - forgejo read + actions read + write + guarded observe - lands code and diagnoses without live mutation.
* **qa** - forgejo read + actions read + write + guarded observe - inspects candidates and grounds verdicts in observed evidence.
* **advisor** - personal overlay role, not shipped in the public bundle - forgejo read + actions read + aws/ssm + tailnet live-observe. The live-observe pair (tailnet + `~/.aws`) stays the documented default for that overlay.
* **director** - forgejo read + actions read + write + aws/ssm + kubectl + runner-token mint + tailnet live-observe - drives the headless lane and fronts incident recovery.
* **ops** - forgejo read + actions read + write + aws/ssm + kubectl + runner-token mint + tailnet live-observe - live system maintenance, the widest tier.

Runner-token mint is `aguard ops forgejo actions generate-runner-token`
for operators. Ward separately mounts the
[role guardfile](../.ward/guardfile.forgejo.runnertoken.kdl) for director and
ops containers. It stays out of the fleet-wide
[readactions overlay](../.ward/guardfile.forgejo.readactions.kdl).

## Read-only observability boundary

[Observe](../.ward/guardfile.observe.kdl) backs Engineer and QA's
`ward ops observe`.
It grants bounded state, logs, events, metrics, health, and rollout status.
Secrets, kubeconfig contents, workload execution, port forwarding, deployment,
rollback, and mutation remain absent.

Approved trace/log/metric readers may project separately without
granting credentials, shell, deploy, or remediation.

## Layer ownership

Each capability is owned by exactly one layer, so a one-layer rollback reads
as drift against this map instead of silently disabling a role.

* **guardfile bindings** - [.ward/roles.kdl](../.ward/roles.kdl), authored here - which guarded verb families a role mounts. Examples are the Engineer/QA observe tier, Forgejo tiers, and ops guardfiles under [aws](../.ward/guardfile.aws.kdl) and [tailscale](../.ward/guardfile.tailscale.kdl). Per ward#578, tailnet and `~/.aws` reach keys off these bindings.
* **role presets** - ward's tree - tagline, capabilities, modes, posture. Stripped from the aos overlay on 2026-07-10 (commit 566f42f) by design, never re-authored here.
* **image binaries** - [docker/dev-base/](dev-base-image.md), authored here - whether language toolchains, `aguard`, `aws`, `kubectl`, `helm`, `tailscale`, `tailscaled`, and the Docker client exist on disk. The one full image contains them all. The `ops` role remains a permission and bring-up boundary, not an image tag.
* **container bring-up** - ward's tree - whether creds and daemons are live: the `~/.aws` dir, a kubeconfig, `tailscaled` process/auth/socket wiring, `FORGEJO_TOKEN`, and the `WARD_CONTEXT_LEVEL` context slice. A binary existing says nothing about this layer.

The 2026-07-10 incident: guardfiles still compiled in, but the binaries,
creds, and daemons under them were gone, and nothing flagged it.

## Live-check ownership

The capability map above is descriptive. If a live probe of the role surface is
still desired, that check belongs in ward's bring-up path, where ward owns the
container state and can make the result authoritative. See ward#1072 for the
ward-owned follow-up path.

## Deferred

Merge authority and commit-status read stay out of this map on purpose: the
ward-native PR workflow capability is foundational ward-side work, and the
specgen also-grant convenience is agentic-os#446.

## See also

* [ward-specs.md](ward-specs.md) - the bundle these guardfiles ship in.
* [dev-base-image.md](dev-base-image.md) - the full image contract.
* [aguard.md](aguard.md) - the operator surface.

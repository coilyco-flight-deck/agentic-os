# Ward Spec Bundle

The aos-hosted deployment bundle for ward's coilyco build input lives directly
in [`.ward/`](../.ward/), flattened alongside `.ward/ward.yaml` (aos#330, first
homed at top-level `ward-specs/`). It carries the forgejo, signoz, ollama,
fleet, and smart-defaults inputs ward consumes.

## Direction of truth

**aos is the source of truth.** Since ward#503, these values are authored here
and flow down into ward at release time. Update `.ward/` in aos and let a push
republish the bundle. The smart-defaults file keeps fleet `direct-main` and only
`coilyco-flight-deck/ward` on `pull-requests-and-merge`.

This is the one allowed exception to the usual config-placement rule. The
bundle is Kai's single coilyco deployment, not fleet config every ward user
melds.

## Release asset

Each aos release attaches `ward-specs-<tag>.tar.gz` plus a `.sha256` sidecar
from [`.forgejo/workflows/release.yml`](../.forgejo/workflows/release.yml). The
tarball is deterministic and enumerates bundle files explicitly, so
`.ward/ward.yaml` never leaks into ward's overlay input.

## How ward consumes it

Ward's brew build and release CI overlay the published asset before building,
then copy its guardfiles over ward's neutral tracked tree. That keeps ward's
tree deployment-agnostic without breaking build-from-source, and the bundle is
the pinned source of truth.

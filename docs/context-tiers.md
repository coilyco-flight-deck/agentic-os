# Role-reachable context tiers (immediate + peripheral)

`check-context-budget` reports the **proactive** tier (eager prompt bytes, per
harness) documented in [context-budget.md](context-budget.md). A driver also
carries context it can reach one tool call away, cheap to provide but a bigger
haystack to pick wrongly from. Two reusable walkers measure it, per clone rather
than per harness, behind the same `count_tokens` chars/4 proxy.

## The two walkers

- **immediate** - a working-dir clone (`/workspace/<name>`), a grep surface not
  in the prompt. `immediate_walk(repo)` returns a `TierWalk(files, bytes, tokens)`
  over `git ls-files` (tracked only, so an untracked build/vendor tree does not
  inflate it). A tracked path that no longer reads is skipped, so the three
  figures stay coherent.
- **peripheral** - the reference repos (`/substrate/<name>`). `peripheral_walk(repos)`
  applies the same walker per repo and returns a `(total, per-repo)` pair. The
  caller passes the repo set - ward passes its substrate mirrors - so this layer
  never enumerates or names a substrate set of its own.

## Token meaning

For a whole-repo walk the token figure is an upper-bound proxy: a driver greps,
it does not ingest every tracked file. So file count and bytes carry the honest
cheap-to-provide signal, and tokens is the ceiling (ward#373 open fork 4).

## The aos/ward split

These are measurement primitives for ward's role-aware three-tier probe
([ward#373](https://forgejo.coilysiren.me/coilyco-flight-deck/ward/issues/373),
`docs/context-probe.md`), which calls them for tiers 2/3 and reuses the doc/skill
accounting for tier 1, then adds its container overlays. Per the
authoring-vs-rollout split, aos owns the generic **measurement** and ward owns
the **role / container / spec-schema** model on top. This layer stays
role-agnostic: the CLI flags take paths, never a role or a substrate set.

## CLI

`--immediate REPO` and `--peripheral REPO` are both repeatable. When present they
append a `role-reachable tiers` section below the per-harness blocks, one aligned
`files / bytes / ~tok` row per clone plus a `peripheral TOTAL`.

## See also

- [context-budget.md](context-budget.md) - the per-harness proactive tier.
- [.ward/ward.yaml](../.ward/ward.yaml) - the `context-budget` verb.

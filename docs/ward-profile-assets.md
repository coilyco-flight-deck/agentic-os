# Ward profile assets

AOS is the public-safe home for Ward profile and config assets that survive the
typed `ProfileProvider` seam.

Ward owns the typed seam and the runtime read path. AOS owns the source bundle
that feeds it, plus any human-readable notes that travel with the assets.

CUE is the validation and composition layer for those assets. YAML stays the
operator-facing authored shape. Rendered outputs are derived artifacts, not a
new hand-authored language.

## Layout

- `.ward/profiles/` - root for Ward profile assets.
- `.ward/profiles/<family>/profile.cue` - family validation and composition
  rules.
- `.ward/profiles/<family>/input.yaml` - operator-facing source data for the
  family.
- `.ward/profiles/<family>/rendered.yaml` - generated output that Ward can
  consume through the typed seam.
- `.ward/profiles/<family>/` - family-owned directory when one profile family
  needs more than one file.
- `.ward/profiles/<family>.kdl` or `.yaml` - single-file families when the typed
  shape stays flat.
- `.ward/profiles/<family>/README.md` - optional public-safe rationale and
  usage notes.
- `.ward/profiles/index.md` - optional cross-family map.

## Rules

- Keep secrets and host-specific values out of this tree.
- Keep CUE close to the profile family it validates so the composition rule is
  reviewable beside the inputs it shapes.
- Do not add an operator-facing migration contract here.
- Do not make Ward fetch runtime config downward from AOS before the typed seam
  exists.

## See also

- [Ward profile CUE pipeline](ward-profile-cue.md)
- [Ward spec bundle](ward-specs.md)
- [Features inventory](FEATURES.md)

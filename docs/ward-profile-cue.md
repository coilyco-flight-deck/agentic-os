# Ward profile CUE pipeline

The Ward profile seam keeps Ward on typed profile data while AOS owns the
public-safe source bundle that feeds it.

CUE sits behind that bundle as the validation and composition engine. YAML is
the operator-facing authored input. CUE checks the shape, applies the profile
rules, and renders the artifact Ward consumes through the typed `ProfileProvider`
seam.

## Source roles

- YAML - the human-authored profile inputs and family overrides.
- CUE - the schema, defaults, and composition rules.
- Rendered output - a derived artifact for Ward, not a new hand-authored surface.

## Expected flow

1. Edit the YAML inputs under `.ward/profiles/<family>/`.
2. Run the CUE composition step for that family.
3. Review the rendered artifact beside the rules that produced it.
4. Hand the rendered result to Ward through the typed seam, not through a
   downward runtime fetch from AOS.

## Guardrails

- Do not treat CUE as an operator-facing required language.
- Do not create a separate ward-profile repo for the composed output.
- Do not add a runtime config dependency from Ward back into AOS.

## See also

- [Ward profile assets](ward-profile-assets.md)
- [Ward spec bundle](ward-specs.md)
- [Features inventory](FEATURES.md)

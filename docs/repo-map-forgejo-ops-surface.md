# Forgejo ops surface discovery

Use this map when the question is "what Forgejo surface exists here now?"

If the same repo also exists under `/substrate`, work in `/workspace/agentic-os`.

## Find the current surfaces

- `ward ops forgejo describe`
- `ward ops forgejo --help`
- `rg -n "gen-ward-ops-reference|ward ops forgejo" docs .ward`

## First check

- `ward ops forgejo describe`

## Notes

- Regenerate the committed render with `ward exec gen-ward-ops-reference` when the surface drifts.
- Prefer the committed reference before guessing a verb name.

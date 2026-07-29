# Forgejo ops surface discovery

Use this map when the question is "what Forgejo surface exists here now?"

If the same repo also exists under `/substrate`, work in `/workspace/agentic-os`.

## Find the current surfaces

- `aosguard ops forgejo describe`
- `aosguard ops forgejo --help`
- `rg -n "aosguard ops forgejo" docs .specgen`

## First check

- `aosguard ops forgejo describe`

## Notes

- Update [aosguard](aosguard.md) when the operator surface changes.
- Prefer runtime help before guessing a verb name.

# Container startup and broker dispatch

Use this map when a run starts wrong, mounts the wrong root, or dispatch wiring looks stale.

If the same repo also exists under `/substrate`, work in `/workspace/agentic-os`.

## Find the current surfaces

- `rg -n "WARD_CONFIG_REF|AOS_REPO_ROOT|ward container up/exec|entrypoint" docker docs .ward`
- `ward exec dev-base-build`
- `ward exec warp doctor`

## First check

- `ward exec dev-base-build`

## Notes

- `ward container up/exec` is the runtime entry point.
- `WARD_CONFIG_REF` and `AOS_REPO_ROOT` are seeded by the entrypoint.

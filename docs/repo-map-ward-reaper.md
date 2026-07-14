# Ward reaper and drain lifecycle

Use this map when a run needs cleanup, reservation release, or drain handling.

If the same repo also exists under `/substrate`, work in `/workspace/agentic-os`.

## Find the current surfaces

- `rg -n "tool_failures|drain|reservation|issue-comment delete" agentic_os docs .ward`
- `ward ops forgejo issue-comment delete --help`
- `ward exec ship-tool-failures -- --dry-run`

## First check

- `ward exec ship-tool-failures -- --dry-run`

## Notes

- The drain path ships tool-use failures.
- The reaper-side cleanup stays discoverable through the search command and the issue-comment delete leaf.

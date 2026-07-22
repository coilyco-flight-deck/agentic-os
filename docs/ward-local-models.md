# Ward Local Model Policy

AOSH selects and records the operator's local model batch. AOS publishes the
OpenCode and Goose selections in the Ward bundle. Ward supplies neutral harness
mechanics and consumes the selected values without embedding Kai-specific model
policy.

## Sources

AOSH's generated `94-pairings.yaml` is the selection source. Its generated
`90-inventory.yaml` records the provisioned model/server pairs. The AOS sync
rejects a selection unless the inventory contains exactly one matching entry
with `keep: true`.

The published values live as sparse top-level agent overlays in
[`agents.kdl`](../.ward/agents.kdl). Ward merges those model values with its
generic OpenCode and Goose launch definitions. The OpenCode endpoint remains an
AOS deployment value beside its model. Goose keeps its existing AOS endpoint.

## Sync and validation

Run `ward exec sync-local-models` from the AOS checkout after AOSH selects a new
batch. The command discovers the sibling AOSH checkout, validates both selected
models against the provisioned inventory, and rewrites only the two model lines.

Run `ward exec sync-local-models -- --check` for a read-only drift check. The
command names each mismatched harness and exits nonzero. AOS's local pre-commit
suite runs that check when the sibling AOSH checkout exists. Public checkouts
without AOSH report a visible skip instead of acquiring a private cross-repo
dependency.

The command accepts `--aosh-root` and `--bundle` for an alternate checkout or a
fixture. A missing or malformed selected roster fails closed.

## See also

- [Ward spec bundle](ward-specs.md)
- [Ward spec overrides](ward-specs-overrides.md)
- [Ward profile assets](ward-profile-assets.md)

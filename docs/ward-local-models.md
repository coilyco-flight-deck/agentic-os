# Ward Local Model Policy

AOSH selects and records role-to-agent-to-model routes. AOS publishes the
selected Goose route in the Ward bundle. Ward supplies neutral harness mechanics
and consumes that selected value without embedding Kai-specific model policy.
The OpenCode model remains deployment-local AOS backend policy. An AOSH role
route does not own or rewrite it.

## Sources

AOSH's generated `94-pairings.yaml` is the Goose selection source. Its generated
`90-inventory.yaml` records the provisioned model/server pairs. The AOS sync
rejects that selection unless the inventory contains exactly one matching entry
with `keep: true`. Unrelated role routes, including engineer through OpenHands,
do not participate in this deployment-local overlay.

The published values live as sparse top-level agent overlays in
[`agents.kdl`](../.ward/agents.kdl). Ward merges those model values with its
generic OpenCode and Goose launch definitions. AOS owns the OpenCode model and
endpoint directly. Goose keeps its existing AOS endpoint while its model follows
the selected AOSH route.

## Sync and validation

Run `ward exec sync-local-models` from the AOS checkout after AOSH selects a new
Goose route. The command discovers the sibling AOSH checkout, validates that
selected model against the provisioned inventory, and rewrites only the Goose
model line.

Run `ward exec sync-local-models -- --check` for a read-only drift check. The
command names the mismatched harness and exits nonzero. AOS's local pre-commit
suite runs that check when the sibling AOSH checkout exists. Public checkouts
without AOSH report a visible skip instead of acquiring a private cross-repo
dependency.

The command accepts `--aosh-root` and `--bundle` for an alternate checkout or a
fixture. A missing or malformed selected roster fails closed.

## See also

- [Ward spec bundle](ward-specs.md)
- [Ward spec overrides](ward-specs-overrides.md)
- [Ward profile assets](ward-profile-assets.md)

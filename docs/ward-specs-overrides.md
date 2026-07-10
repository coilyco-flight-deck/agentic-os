# Ward Role Overrides

The coilyco ward-specs bundle keeps two layers in `.ward/roles.kdl`:

* Role metadata. `tagline`, `capabilities`, `modes`, `posture`, and `guardfile`
  nodes describe the role itself.
* Per-harness overlays. `agent <name> { ... }` blocks retune a specific agent
  for that role without changing the top-level agent defaults.

cli-guard parses those overlay blocks into `RoleAgentOverride` entries keyed by
agent name. ward applies them at dispatch, so a role can override `model`,
`endpoint`, `reasoning-effort`, or `verbosity` for one harness while leaving
the baseline fleet agent unchanged.

This bundle currently uses the overlay layer for:

* `director` - `claude` and `codex` both use `xhigh` reasoning effort, with
  `claude` pinned to `claude-opus-4-8` and `codex` pinned to `gpt-5.5`.
* `advisor` - `claude` and `codex` both use `high` reasoning effort, with the
  same model pins as `director`.
* `ops` - `claude` and `codex` both use `xhigh` reasoning effort, with the same
  model pins as `director`.

The bundle shape is documented in `docs/ward-specs.md`, and the release tarball
packages `.ward/` recursively with `ward.yaml` excluded so the overlay blocks
stay shipped without a hand-maintained file list.

## See also

* [ward-specs.md](ward-specs.md) - the bundle overview and runtime path.
* [AGENTS.md](../AGENTS.md) - the public-safe config-placement rule and the
  carved exception for this bundle.

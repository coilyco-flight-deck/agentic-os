# Role surface tiers

The intended capability surface each `ward agent` container role carries. The
Forgejo runner-token mint path was pulled out of the broader read-actions
overlay and kept on the tighter director/ops surface.

## Tiers

- `engineer` - Forgejo read + actions read + write.
- `qa` - Forgejo read + actions read + write.
- `advisor` - Forgejo read + actions read + aws live-observe.
- `director` - Forgejo read + actions read + write + aws + kubectl + runner-token mint.
- `ops` - Forgejo read + actions read + write + aws + kubectl + runner-token mint.

Runner-token mint is `ward ops forgejo actions generate-runner-token`, backed by
the fetch overlay in
[`.ward/guardfile.forgejo.runnertoken.kdl`](../.ward/guardfile.forgejo.runnertoken.kdl).

## Layer ownership

- `roles.kdl` - the guardfile bindings that grant each role its surface.
- `guardfile.forgejo.runnertoken.kdl` - the declarative fetch overlay for the
  registration-token routes.
- `guardfile.forgejo.runnertoken.exec.kdl` - the thin exec bridge that exposes
  the user-facing command.
- `forgejo-runner-token.py` - the tiny scope router that picks the fetch leaf.

## See also

- [ward-specs.md](ward-specs.md)
- [Forgejo runner-token fetch overlay](forgejo-runner-token.md)

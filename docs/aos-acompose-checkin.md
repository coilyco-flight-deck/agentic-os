---
doc_goal: Define the ergonomic composed-role check-in and its agent-owned defaults.
---
# AOS composed-role check-in

`acompose-checkin` asks a composed role to identify and describe itself without
requiring the operator to repeat an agent's non-interactive invocation policy.

## Invocation

```bash
aos --role engineer --agent codex acompose-checkin
```

`--role` selects the agent-compose role. `--agent` selects the executable
adapter and its defaults. Codex is the first supported adapter.

## Codex adapter

The adapter runs `codex exec` with an ephemeral session, a read-only sandbox,
no color, and no Git-repository requirement. The container supplies its
Terra-medium defaults and stages known Codex auth through the normal AOS path.

The check-in skips the general substrate while retaining the AOS provider
required to compose the role. A conflicting explicit `--layout` fails instead
of projecting one harness and executing another.

The prompt forbids tool use and asks the agent to begin with
`ROLE-CONFIRMED: <role>`, then describe itself in under 180 words. The CLI
prints the response without interpreting it. The role-question harness remains
the assertion path for an automated pass or fail.

The diagnostic transcript stays streaming in emission order. A duplicated
final stdout copy is suppressed. Blank lines frame the transcript, each Codex
section divider, and each prompt, warning, response, or token block.

## Inspection

Global `--image`, `--delivery`, `--auth`, and `--dry-run` behavior still
applies. A dry run renders the Docker launch without exposing auth or forwarded
environment values.

## See also

* [aos-cli.md](aos-cli.md) - container launch and substrate contract.
* [test-harness-composed-roles.md](test-harness-composed-roles.md) - automated role confirmation.

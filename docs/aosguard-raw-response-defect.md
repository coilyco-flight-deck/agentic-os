# The aosguard raw-response defect

`aosguard ops forgejo action-job logs` and `action-run logs` fail on every call:

```text
$ aosguard ops forgejo action-job logs coilyco-gaming sirens-echo 33908
aosguard: invalid character '-' after top-level value
```

The `-` is the first byte of the log's leading timestamp. The run variant fails
on `'P'`, the first byte of a ZIP's `PK` magic. Every output mode and `--query`
fail identically, and `--dry-run` shows a correct request, so the request is
right and the response handling is wrong. `action-run-job list` is unaffected.

## Where the defect is

Not in the guardfile, and not in the vendored spec. Both the vendored Forgejo
snapshot and the committed lock already declare `produces: text/plain` and
`produces: application/zip` for these two operations, and the engine's
`rawResponseOp` reads that correctly, returning true for both.

The engine then throws the answer away. `Runtime.FireCapture` JSON-decodes every
success body and returns a coded error, and both call sites check their raw-response
flag only *after* that call returns. The decode fails first, so the raw branch
was unreachable and setting the flag changed nothing.

## Why the guardfile cannot patch around it

The `output "raw"` node exists, but only on `fetch` overlays. A `can` grant body
accepts `op`, `body`, `message`, and `describe`, and nothing else:

```text
guardfile: grant body: unknown node "output"
    (want op | body | message | describe; fail-closed)
```

So there is no authoring-layer workaround. The fix belongs upstream, which is
where it went: umbra#291, part one of umbra#289.

## What to use meanwhile

Nothing is unreachable. `aosguard ops actions logs` is a guarded leaf over the
same official API, it resolves visible run and job identifiers rather than
internal database ids, and it returns bytes exactly. `ward exec
forgejo-actions-logs` runs the same `agentic_os.forgejo_actions_logs` module.

Never fall back to a `curl` with an SSM-resolved token. That is a secret-handling
action, and it is not needed here.

## Removing this page

This note comes out when `.specgen/guardfiles/specverb.lock` re-locks onto an
umbra release carrying umbra#291. The lock currently pins `v0.139.0`. Re-lock
with `just aosguard-lock`, then confirm the leaf returns log bytes and delete
this page along with the pointer in
[Forgejo Actions logs](forgejo-actions-logs.md).

## See also

* [Forgejo Actions logs](forgejo-actions-logs.md) - the working resolved command.
* [aosguard](aosguard.md) - the operator CLI and its build contract.

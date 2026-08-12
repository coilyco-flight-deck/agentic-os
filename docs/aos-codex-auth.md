---
doc_goal: Define fail-closed Codex authentication for standalone AOS launches.
---
# Standalone Codex authentication

Standalone AOS launches default to `--auth=true`. When Codex is selected, AOS
requires supported environment, file-backed, or macOS Keychain credentials
before it starts Docker.

## Host discovery

`CODEX_API_KEY`, `CODEX_ACCESS_TOKEN`, and the compatibility `OPENAI_API_KEY`
cross the container boundary by name when present. Otherwise, AOS resolves
`auth.json` under `CODEX_HOME`. When `CODEX_HOME` is unset, it uses
`~/.codex/auth.json`, matching Codex's default. The file must be readable,
regular, valid JSON, and contain file-backed API-key or token data. AOS reports
missing, unreadable, non-file, and unsupported credentials without printing
credential values or file contents.

When the file is absent on macOS, AOS reads Codex's direct `Codex Auth`
Keychain record for the resolved `CODEX_HOME`. It writes the returned auth JSON
to a private `0700` temporary directory as a `0600` file, mounts that file
read-only, and removes the directory after the Docker command or dry run ends.
The Keychain value is never printed or placed in Docker arguments or environment
variables.

Codex's encrypted secrets backend stores `secrets/codex_auth.age` on disk and
only its passphrase in the keyring. Standalone AOS does not reimplement that
cryptographic format. It reports the backend as unsupported before Docker
starts. Direct keyring projection is currently macOS-only. Other platforms
require environment or file-backed auth.

## Container staging

The selected host auth projection mounts at `/run/aos/auth/codex.json`
read-only. Container bootstrap copies it into the tmpfs-backed
`$CODEX_HOME/auth.json` with mode `0600`, then hands the ephemeral HOME to
Codex. The host HOME and credential store never mount into the container.

Discovery and validation finish before AOS builds or executes the Docker launch.
Dry-run output contains only the auth path and mount shape, never auth contents.

A dry run starts no container, so it treats unusable credentials as a
diagnostic rather than a wall. AOS reports the same message on stderr and still
renders the plan, which then carries no auth mount because none was staged.
Only a real launch fails closed. A caller that wants neither the projection nor
the report passes `--auth=false`.

## Startup and inference proofs

`--auth=false` remains available for deliberate unauthenticated commands and
omits authentication environment variables as well as file staging. The
`aos-standalone-composition-smoke` Ward verb uses it with `codex --version`, so
that smoke proves composition and harness startup only.

`ward exec aos-role-question -- cloud design` uses the default authenticated
path and asks Codex a public-safe question. A successful response proves the
separate authenticated inference boundary.

## See also

* [aos-cli.md](aos-cli.md) - standalone and Ward-governed launch contract.
* [aos-acompose-checkin.md](aos-acompose-checkin.md) - bounded Codex check-in.
* [test-harness-composed-roles.md](test-harness-composed-roles.md) - role probes.

---
doc_goal: Define fail-closed Claude authentication for standalone AOS launches.
---
# Standalone Claude authentication

Standalone AOS launches default to `--auth=true`. When Claude is selected, AOS
requires supported environment, file-backed, or macOS Keychain credentials
before it starts Docker, mirroring [aos-codex-auth.md](aos-codex-auth.md).

## Host discovery

`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `CLAUDE_CODE_OAUTH_TOKEN`
cross the container boundary by name when present, so nothing is projected.

Otherwise AOS resolves `~/.claude/.credentials.json`. The file must be readable
and regular. AOS reports unreadable and non-file credentials without printing
credential values or file contents.

When that file is absent on macOS, AOS reads Claude Code's Keychain record and
writes it to a private temporary file mounted read only. Claude Code namespaces
the record by a digest of `CLAUDE_CONFIG_DIR`, so AOS resolves the service the
same way the harness does: the default directory keeps the bare
`Claude Code-credentials` service and any other directory takes the digest
suffix. See [native-claude-credentials.md](native-claude-credentials.md).

The container copies the mounted file to `~/.claude/.credentials.json`, the
path Claude Code reads.

## Fail closed

An absent credentials file is not an absence of credentials, because macOS
keeps the login in the Keychain. AOS previously treated a missing file as
"nothing to stage" and started the container anyway, which composed the role,
projected it, and only then reported `Not logged in`.

Discovery now fails before Docker starts and names the three ways forward: run
`claude /login` on the host, export `ANTHROPIC_API_KEY`, or pass `--auth=false`
for unauthenticated commands.

A dry run starts no container, so it reports the same message on stderr and
still renders the plan, matching
[aos-codex-auth.md](aos-codex-auth.md#container-staging).

## See also

* [aos-codex-auth.md](aos-codex-auth.md) - the Codex credential path this mirrors.
* [native-claude-credentials.md](native-claude-credentials.md) - the native lend-and-harvest bridge.

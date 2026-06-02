---
name: tooling-gpg-ssm
description: gpg-ssm is a GPG wrapper that pulls signing passphrases from AWS SSM at sign time instead of caching on disk. Use when wiring up a new host for signed commits, rotating a per-host key, or debugging signing failures. Triggers - gpg-ssm, gpg signing, signed commits.
---

# gpg-ssm

GPG wrapper script that fetches the signing-key passphrase from AWS SSM at sign time, instead of caching it in Keychain or anywhere else on disk. Stolen-laptop scope is one key, not the whole identity.

## Files

- `~/projects/coilyco-flight-deck/agentic-os/scripts/gpg-ssm` - the wrapper (bash). Symlinked to `~/.local/bin/gpg-ssm` by `agentic-os/setup.sh`.
- `~/projects/coilyco-flight-deck/agentic-os/scripts/gpg-ssm.cmd` - Windows shim for Git for Windows, which can't reliably invoke an extensionless shebang script. It's a `bash.exe` re-entry.

## Wire-up

```bash
git config --global gpg.program "$HOME/.local/bin/gpg-ssm"
```

Windows: same idea, point at `gpg-ssm.cmd`.

## Deeper context

- [design](references/design.md) - per-host keys, no on-disk passphrase, verification passthrough, agent cache, credential gate, plus the Git Bash carve-out.
- [adding a new host](references/adding-a-host.md) - six steps to wire signed commits on a fresh machine.
- [debugging](references/debugging.md) - common signing failures, fixes, and the never-bypass rule.

## See also

- Canonical script: `~/projects/coilysiren/agentic-os/scripts/gpg-ssm`
- Windows shim: `~/projects/coilysiren/agentic-os/scripts/gpg-ssm.cmd`
- Install snippets per OS: `~/projects/coilysiren/agentic-os/README.md`
- SSM param inventory: `~/projects/coilysiren/<personal-os-repo>/SSM.md`

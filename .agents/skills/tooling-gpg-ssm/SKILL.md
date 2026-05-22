---
name: tooling-gpg-ssm
description: gpg-ssm is a GPG wrapper that pulls signing passphrases from AWS SSM at sign time instead of caching on disk. Use when wiring up a new host for signed commits, rotating a per-host key, or debugging signing failures. Triggers - gpg-ssm, gpg signing, signed commits.
---

# gpg-ssm

GPG wrapper script that fetches the signing-key passphrase from AWS SSM at sign time, instead of caching it in Keychain or anywhere else on disk. Stolen-laptop scope is one key, not the whole identity.

## Files

- `~/projects/coilysiren/agentic-os/scripts/gpg-ssm` - the wrapper (bash). Symlinked to `~/.local/bin/gpg-ssm`.
- `~/projects/coilysiren/agentic-os/scripts/gpg-ssm.cmd` - Windows shim for Git for Windows, which can't reliably invoke an extensionless shebang script. It's a `bash.exe` re-entry.

## Wire-up

```bash
git config --global gpg.program "$HOME/.local/bin/gpg-ssm"
```

Windows: same idea, point at `gpg-ssm.cmd`.

## Design

**Per-host keys.** Each machine has its own GPG keypair. `git config --global --get user.signingkey` returns the local keyid. SSM param path: `/coilysiren/gpg-passphrase/<keyid>` (SecureString). Each host's wrapper resolves its own param. Stolen laptop burns one key, not the identity.

**No on-disk passphrase.** The wrapper hands the passphrase to gpg via `--passphrase-fd 3` with a process substitution (`3< <(printf '%s' "$pass")`). No command-line exposure (would show in `ps`), no temp file, no Keychain entry.

**Verification passthrough.** Non-signing gpg invocations (verify, list-keys, etc.) skip the SSM round-trip entirely: `exec gpg "$@"`. The argv parser at the top of the script sets `needs_sign=1` only on `--sign`, `--clearsign`, `--clear-sign`, `--detach-sign`, or any short-bundle flag containing `s` (catches `-bs`, `-bsau` which git uses).

**gpg-agent cache reuse.** After the first successful sign in a session, gpg-agent caches the unlocked key in memory. Subsequent signs hit the cache, not SSM, provided `default-cache-ttl` in `gpg-agent.conf` is set long enough (recommended ~1yr).

**Fail-fast credential gate.** Before fetching from SSM, the wrapper runs `coily ops aws sts get-caller-identity`. If AWS creds are expired or missing, the error message names the next dictation: `Run 'aws sso login' and retry.` Opaque "failed to fetch" errors are a design smell here - the gate exists so the user knows exactly what to dictate.

## Git Bash carve-out

MSYS / Git Bash mangles leading-slash args into Windows paths, which would corrupt the SSM param name `/coilysiren/gpg-passphrase/...` into something like `C:/Program Files/Git/coilysiren/gpg-passphrase/...`. The wrapper opts out:

```bash
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) export MSYS_NO_PATHCONV=1 ;;
esac
```

If a Windows host suddenly can't find the SSM param, suspect this got reverted before suspecting SSM permissions.

## Adding a new host

1. Generate a fresh GPG keypair on the host (`gpg --full-generate-key`, ed25519 or rsa4096).
2. Set the local `user.signingkey` to the new keyid: `git config --global user.signingkey <KEYID>`.
3. Stash the passphrase: `coily ops aws ssm put-parameter --name /coilysiren/gpg-passphrase/<KEYID> --type SecureString --value FILL_ME_IN`.
4. Update `SSM.md` in `<personal-os-repo>/` with the new param row.
5. Export the public key, upload to GitHub (`Settings -> SSH and GPG keys`).
6. Test: `echo test | gpg --clearsign` should round-trip through the wrapper.

## Debugging

- **`user.signingkey is unset`** - run `git config --global user.signingkey <KEYID>`. The keyid comes from `gpg --list-secret-keys --keyid-format LONG`.
- **`AWS credentials expired or missing`** - the message says it: `aws sso login` (or `coily ops aws sso login`), retry.
- **`failed to fetch /coilysiren/gpg-passphrase/<keyid>`** - param doesn't exist or IAM denies. Check `coily ops aws ssm get-parameter --name /coilysiren/gpg-passphrase/<keyid> --with-decryption` directly. If 404, you skipped step 3 above.
- **Sign succeeds but GitHub shows "Unverified"** - public key not uploaded, or wrong email on the GPG uid vs `user.email`. Check `gpg --list-keys` against the GitHub signing-keys page.
- **Hangs forever** - gpg-agent prompting for the passphrase via pinentry, meaning `--pinentry-mode loopback` got dropped or gpg-agent is in a weird state. Restart: `gpgconf --kill gpg-agent`.

## Never bypass

The temptation is real: "I'm in a hurry, let me just `git commit --no-gpg-sign`" or `git config --global commit.gpgsign false` for a session. Don't. Signed commits are a <personal-os-repo> pre-commit hook expectation across repos. If `gpg-ssm` is genuinely broken, fix it (or temporarily comment out the `gpg.program` line and remember to put it back). Bypassing leaves unsigned commits in history that look identical to spoofed ones.

## See also

- Canonical script: `~/projects/coilysiren/agentic-os/scripts/gpg-ssm`
- Windows shim: `~/projects/coilysiren/agentic-os/scripts/gpg-ssm.cmd`
- Install snippets per OS: `~/projects/coilysiren/agentic-os/README.md`
- SSM param inventory: `~/projects/coilysiren/<personal-os-repo>/SSM.md`

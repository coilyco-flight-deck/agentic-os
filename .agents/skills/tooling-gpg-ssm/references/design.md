# gpg-ssm design

**Per-host keys.** Each machine has its own GPG keypair. `git config --global --get user.signingkey` returns the local keyid. SSM param path: `/coilysiren/gpg-passphrase/<keyid>` (SecureString). Each host's wrapper resolves its own param. Stolen laptop burns one key, not the identity.

**No on-disk passphrase.** The wrapper hands the passphrase to gpg via `--passphrase-fd 3` with a process substitution (`3< <(printf '%s' "$pass")`). No command-line exposure (would show in `ps`), no temp file, no Keychain entry.

**Verification passthrough.** Non-signing gpg invocations (verify, list-keys, etc.) skip the SSM round-trip entirely: `exec gpg "$@"`. The argv parser at the top of the script sets `needs_sign=1` only on `--sign`, `--clearsign`, `--clear-sign`, `--detach-sign`, or any short-bundle flag containing `s` (catches `-bs`, `-bsau` which git uses).

**gpg-agent cache reuse.** After the first successful sign in a session, gpg-agent caches the unlocked key in memory. Subsequent signs hit the cache, not SSM, provided `default-cache-ttl` in `gpg-agent.conf` is set long enough (recommended ~1yr).

**Fail-fast credential gate.** Before fetching from SSM, the wrapper runs `coily ops aws sts get-caller-identity`. If AWS creds are expired or missing, the error message names the next command: `Run 'aws sso login' and retry.` Opaque "failed to fetch" errors are a design smell here - the gate exists so the user knows exactly what to run.

## Git Bash carve-out

MSYS / Git Bash mangles leading-slash args into Windows paths, which would corrupt the SSM param name `/coilysiren/gpg-passphrase/...` into something like `C:/Program Files/Git/coilysiren/gpg-passphrase/...`. The wrapper opts out:

```bash
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) export MSYS_NO_PATHCONV=1 ;;
esac
```

If a Windows host suddenly can't find the SSM param, suspect this got reverted before suspecting SSM permissions.

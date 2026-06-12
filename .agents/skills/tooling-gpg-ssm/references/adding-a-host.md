# Adding a new host

1. Generate a fresh GPG keypair on the host (`gpg --full-generate-key`, ed25519 or rsa4096).
2. Set the local `user.signingkey` to the new keyid: `git config --global user.signingkey <KEYID>`.
3. Stash the passphrase: `ward ops aws ssm put-parameter --name /coilysiren/gpg-passphrase/<KEYID> --type SecureString --value FILL_ME_IN`.
4. Update `SSM.md` in `<personal-os-repo>/` with the new param row.
5. Export the public key, upload to GitHub (`Settings -> SSH and GPG keys`).
6. Test: `echo test | gpg --clearsign` should round-trip through the wrapper.

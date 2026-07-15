# Forgejo org-repo bootstrap

`ward exec forgejo-org-repo-bootstrap` creates or reconciles an org repo on
Forgejo using the admin token from SSM. It exists for the hand-created GitHub
profile mirrors that need Forgejo repo metadata fixed even when `coilyco-ops`
only has write access.

## Why it exists

The regular `ward ops forgejo org-repo create` leaf rides the coilyco-ops bot
token. That is enough on repos where Forgejo honors org creation, but it can
still stop short of making a hand-created mirror public or updating its
description.

This helper takes the admin route so the operator can bootstrap or reconcile
the mirror in one step.

## Example

```sh
ward exec forgejo-org-repo-bootstrap -- coilyco-bridge .github \
  --description "Profile README for coilyco-bridge" --public
```

The same flow applies to `coilyco-flight-deck/.github`.

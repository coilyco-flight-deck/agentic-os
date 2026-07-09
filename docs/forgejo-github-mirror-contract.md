# Forgejo-canonical GitHub mirror contract

This is the default public-repo contract for repos that are canonical on
Forgejo and mirrored to GitHub.

## Authority

- Forgejo owns release and tag creation.
- GitHub mirrors are downstream copies only.
- GitHub does not become a second release source unless a concrete consumer
  needs that surface.

## Default surface

- Create the release and public tag on Forgejo.
- Mirror `main` to GitHub fast-forward-only.
- Mirror `v*` tags to GitHub append-only.
- Treat GitHub Releases as optional, not required.

## GitHub Releases

GitHub Releases are not part of the default public surface. If a repo needs one
for a downstream consumer, the release should be derived from the Forgejo tag
or release metadata so Forgejo stays the single source of truth.

## Divergence recovery

If GitHub `main` diverges from Forgejo `main`, the mirror job should fail red
instead of forcing history. A human reconcile is a one-time repair, not a
routine release step.

## Shared implementation

No separate workflow template is required yet. The reusable part is the
contract itself, while the repo-local `release.yml` and `mirror-to-github.yml`
jobs implement the policy for a given repo.

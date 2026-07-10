# Forgejo Actions log bridge

The `.ward/forgejo-actions-logs.sh` bridge fetches the live plaintext job log
from Forgejo's web route and prints it raw to stdout. It is packaged with the
coilyco ward spec bundle, but latest ward does not mount it as
`ward ops forgejo actions logs`: the spec-driven `ward ops forgejo` command owns
that path, and same-path exec overlays are skipped fail-closed.

Why the bridge still exists:

- Forgejo 15.0.2 exposes the Actions metadata in swagger, but not this log
  route.
- The script preserves the owner gate and Forgejo token auth, and it does not
  JSON-render the response body.
- ward#950 tracks replacing this bridge with a first-class fetch-style ward-kdl
  surface that can live beside the spec-driven Forgejo verbs.

The route is:

`GET /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job}/attempt/{attempt}/logs`

See also:

- [ward-specs.md](ward-specs.md)
- [Cross-repo tooling and release](FEATURES.md)

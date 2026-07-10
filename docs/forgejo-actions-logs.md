# Forgejo Actions log streaming

`ward ops forgejo actions logs <owner> <repo> <run-index> <job-index> <attempt>`
streams the live plaintext job log from Forgejo's web route and prints it raw to
stdout.

Why it is separate:

- Forgejo 15.0.2 exposes the Actions metadata in swagger, but not this log
  route.
- The ward spec bundle keeps the existing spec-derived Forgejo surface, then
  overlays this raw log bridge as a separate exec member.
- The bridge preserves the owner gate and Forgejo token auth, and it does not
  JSON-render the response body.

The route is:

`GET /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job}/attempt/{attempt}/logs`

See also:

- [ward-specs.md](ward-specs.md)
- [Cross-repo tooling and release](FEATURES.md)

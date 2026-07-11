# Forgejo Actions rerun bridge

The `.ward/forgejo-actions-rerun.sh` and
`.ward/forgejo-actions-rerun-failed-jobs.sh` bridges re-run an existing Forgejo
Actions workflow run by visible run id. They stay narrow on purpose. The call
targets a known run, not a workflow file, so it cannot dispatch an arbitrary
workflow by mistake.

Why the bridge exists:

- Forgejo exposes the rerun routes on the live deployment, but the pinned
  swagger lock does not surface them as first-class ward leaves.
- The rerun bridge keeps the admin PAT in the ward bundle and keeps the run id
  as the only authority boundary.
- `actions rerun` re-runs the full run.
- `actions rerun-failed-jobs` re-runs only the failed jobs in that run.

The resolved routes are:

- `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun`
- `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs`

See also:

- [ward-specs.md](ward-specs.md)
- [Forgejo Actions log bridge](forgejo-actions-logs.md)
- [Cross-repo tooling and release](FEATURES.md)

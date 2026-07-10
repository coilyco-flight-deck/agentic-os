# Forgejo Actions list bridge

The `.ward/forgejo-actions-list.sh` bridge lists Forgejo Actions runs or tasks
and defaults to `page=1` when the caller omits `--page`. That keeps CI checks on
the first page instead of accidentally pulling the whole history when `limit`
is present.

Use the safe ward surface for live inspection:

- `ward ops forgejo actions runs <owner> <repo> [--page 1] [--limit N]`
- `ward ops forgejo actions tasks <owner> <repo> [--page 1] [--limit N]`

Raw API examples should include `page=1` whenever they include `limit`:

- `GET /api/v1/repos/{owner}/{repo}/actions/runs?page=1&limit=1`
- `GET /api/v1/repos/{owner}/{repo}/actions/tasks?page=1&limit=1`

See also:

- [Forgejo Actions log bridge](forgejo-actions-logs.md)
- [Ward spec bundle](ward-specs.md)

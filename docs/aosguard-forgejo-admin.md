# The Forgejo admin wrapper

`forgejo-admin` holds repo settings and cosmetics, org labels, repo topics, and
branch protection. Forgejo refuses every one of them to `coilyco-ops`, which is
an org member holding push rather than an owner holding repo-admin, so the
credential is already a sufficient gate. An earlier revision also narrowed each
action to its safest field - `repo edit` accepted a description and nothing
else. That was a second gate on top of a sufficient one, and it cost more than
it bought: repo merge policy and branch protection are converged often enough
that the fallback was hand-running a script or editing the web UI. `repo edit`
now exposes the whole `EditRepoOption`, which is also the field set
`infrastructure/scripts/forgejo-repo-settings.py` converges.

Two fields ride along rather than being blocked. `private` flips visibility and
`archived` flips lifecycle, and the ordinary wrapper still denies archive and
points at the web UI. Both are reachable here because anyone who can reach this
wrapper can already do either in the UI in fewer steps.

Deletes stay marked. `org-label delete` removes the label from every issue
carrying it, so the guardfile names `edit org-label` as the rename path: an edit
keeps the label id and every issue keeps its association.

Org-label writes on the ordinary wrapper are `never` leaves that name the admin
verb. They previously answered a bare `403 Must be an organization owner`, which
is true and tells the caller nothing about where to go.

## Credentials

The PAT comes from `/forgejo/admin-token` through the same `provider ssm` block
the ordinary wrapper uses, resolved at call time. There is no environment
variable to export and no wrapper script to run first. Access to the parameter
is the boundary, which is where an SSM-backed credential's boundary belongs.

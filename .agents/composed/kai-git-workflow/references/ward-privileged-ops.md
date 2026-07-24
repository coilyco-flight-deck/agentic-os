# Privileged ops via ward

Reach for `ward gh ...`, `ward ops aws ...`, `ward kubectl ...`, `ward systemctl ...` etc. for privileged ops. Bare invocations of the *write* surface are denied by lockdown - destructive verbs (gh pr create/edit/merge, aws s3 cp, kubectl apply/delete, etc.) only work through ward, which gates them on argv validation and writes the audit row.

**Read verbs are explicitly allowed bare** (`aws s3 ls`, `gh pr view`, `kubectl get pods`, etc.) - lockdown's allow list enumerates them, and bare reads are fine to use directly when convenient. The "everything through ward" rule that used to live here was always a hygiene preference rather than a security boundary, and it was stricter than what lockdown actually enforces.

`ward gh` / `ward ops aws` / `ward kubectl` are now thin pass-throughs - they take the same args as the underlying CLI verbatim, no flag parsing on ward's side. **Limitations:** ward rejects shell metacharacters in argv (no `|`, `&`, `>` inside an argument), so pipe / redirect *outside* the ward call (`ward gh ... > /tmp/x.json`) is fine but keep them out of any single arg.

## Disabling pull requests on a repo

GitHub's per-repo "disable pull requests" toggle (shipped Feb 2026) must be set via **GraphQL**, not REST. This is a sanctioned exception to the REST-default rule: the REST path is broken. `has_pull_requests` on `PATCH /repos/{owner}/{repo}` echoes whatever you send but does not persist, and the REST `GET` reads back stale/inverted values - do not trust it to confirm state. GraphQL `Repository.hasPullRequestsEnabled` is authoritative both to read and to write.

```graphql
# resolve the repo node id (and read current state)
query { repository(owner:"coilysiren",name:"REPO"){ id hasPullRequestsEnabled } }
# disable PRs
mutation { updateRepository(input:{repositoryId:"R_...",hasPullRequestsEnabled:false}){ repository{ name hasPullRequestsEnabled } } }
```

`pullRequestCreationPolicy` (`ALL` / `COLLABORATORS_ONLY`) is the softer "who can open PRs" dropdown, also on `updateRepository`. Pass the query as a file - `ward ops gh api graphql -F query=@/tmp/q.graphql` - because ward's metacharacter gate rejects the `{ }` in an inline `-f query=...` arg. Origin: the Forgejo API contract.

# Repository residency

Agent Compose owns repository policy and emits the strict
`~/.agent-compose/repository-plan.yaml`. AOS validates that machine contract and
exposes its host-residency projection without parsing `.agents/roles.kdl`:

```sh
aos repositories --format lines
aos repositories --format json
```

The JSON surface uses `aos.repository-residency.v1`. It retains the compiled
absolute projects root and each owner-qualified selection's source, scope,
reason, and provider details. Lines output contains only sorted
`owner/repository` identities for shell consumers.

AOS consumes Agent Compose's `agent-compose.repositories.v2` YAML contract and
temporarily accepts the preceding v1 JSON contract during host rollout. When
both files exist, YAML wins. AOS rejects unknown fields, unknown formats, unsafe
identities, duplicate or unsorted selections, incomplete provenance, relative
roots, and paths outside the compiled projects root. Missing or invalid plan
state fails closed. There is no embedded repository fallback and doctrine
source paths never become repository policy.

Native workspace projection and cleanup use the same compiled residency set.
The status-line tracker compares exact owner-qualified checkouts against it.
Infrastructure uses it to clone missing resident repositories and fetch
existing remotes without changing a worktree.

This host-residency projection is distinct from Ward's baked container
substrate. It also grants no role access by itself. Role selection is sealed
into the verified Agent Compose bundle that AOS adapts for Ward.

## See also

* [Native workspaces](native-agent-workspaces.md) - worktree projection and cleanup.
* [Repo tracker](repo-tracker.md) - stray-checkout status line.
* [AOS context bundle](aos-context-bundle.md) - selected role handoff.

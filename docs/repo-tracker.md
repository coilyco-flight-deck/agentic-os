# Repo-checkout tracker

A project-local status-line row names git checkouts on disk that are not in
Agent Compose's compiled host residency, meaning the strays to remove.

The canonical implementation is the dev-base
[`20-repos.sh`](../docker/dev-base/statusline.d/20-repos.sh) provider for the
[status-line composer](statusline.md). A warded container shows this row and
self-suppresses where there is nothing to scan. Repositories can override or
adopt the same provider through `.agentic-os/statusline.d/`.

## What it shows

When every checkout is resident, the row shows a green all-clear and count:

```text
📦 15 repos, none stray
```

When compiled residency omits on-disk checkouts, the row names the first few
and collapses the rest into `+N more`. A few strays are orange. Four or more are
bold red:

```text
📦 7 to remove: coilyco-bridge/agentic-os-hardware, coilyco-bridge/deploy, coilysiren/lore, coilyco-flight-deck/ward, +3 more
```

When the AOS projection is unavailable, the row degrades to the checkout count
without claiming that anything is stray.

## Expected residency

The provider runs `aos repositories --format lines`. AOS strictly validates
Agent Compose's compiled plan before returning sorted `owner/repository`
identities. The tracker carries no repository names, parses no policy, and has
no fallback roster. `$AOS_BIN` may select the AOS executable.

## Fleet-org scope

Only checkouts under the configured fleet owners are considered, so third-party
upstreams never read as strays. Owner names come from `$AOS_FLEET_ORGS`, else
`~/.config/agentic-os/fleet-orgs.txt`. With no owner list, every owner directory
is in scope.

## Scan contract

* The root is `~/projects`, overridable through `$AOS_REPOS_ROOT`.
* `<root>/<owner>/<repository>` counts as a checkout when `.git` exists as a
  file or directory.
* Matching uses exact `owner/repository` identity. Same-named repositories
  under different owners remain distinct.
* The scan performs only shallow directory and `.git` checks.

## Reuse

A repository can adopt the provider by placing a copy or symlink at
`.agentic-os/statusline.d/20-repos.sh` and marking it executable. AOS supplies
residency. The fleet-org input controls scan scope. The status-line composer
discovers the provider for sessions rooted there.

## See also

* [Repository residency](repository-residency.md) - strict machine projection.
* [Status line](statusline.md) - provider composition.

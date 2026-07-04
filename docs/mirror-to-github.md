# Mirror to GitHub

`.forgejo/workflows/mirror-to-github.yml` keeps the read-only GitHub mirror
(`coilysiren/agentic-os`) in step with canonical Forgejo `main`. GitHub is where
the fleet's `uses: coilysiren/agentic-os/actions/*@main` references resolve, so
the mirror advancing matters even though Forgejo is upstream-of-record. The job
no-ops without the `GITHUB_MIRROR_PAT` secret.

## Fast-forward-only, never `--force`

GitHub `main` carries a "cannot force-push" branch-protection rule - that rule
**is** the PR gate that makes GitHub the PR-gated downstream mirror. So the
mirror push is fast-forward-only:

- `git push github main` (no `--force`) - fails if the push is not a
  fast-forward, which is what we want against a protected branch.
- `git push --tags github` - tags are append-only, never force-updated.

Forgejo `main` is itself append-only (no force-push upstream), so in steady
state every Forgejo push is a descendant of the GitHub tip and fast-forwards
cleanly. If a push is ever rejected the job now **fails red with a remediation
message** instead of forcing into the protected branch and stalling silently.

The old job ran `git push --force github main`, which GitHub rejected outright
(`GH013`). Because nobody watches mirror CI, the mirror sat ~2 weeks stale while
Forgejo advanced 237+ commits (agentic-os#309). Same failure hit
`session-lattice`; mirror repos without the force-push rule synced fine.

## One-time reconcile (divergence recovery)

A rejected fast-forward means GitHub `main` carries commits that are **not**
ancestors of Forgejo `main` - the histories diverged (e.g. GitHub-only hotfixes
whose content was later relanded on Forgejo under different SHAs). The mirror
cannot heal this itself without a `--force`, which the branch-protection rule
forbids, so it takes a **one-time human reconcile** by a GitHub admin:

1. On GitHub, confirm the divergent commits are already relanded on Forgejo by
   content, so nothing is lost by resetting.
2. Temporarily lift the "cannot force-push" rule on `main` (or use an admin
   bypass), then `git push --force github <forgejo-main-sha>:main`.
3. Re-enable the rule.

After the reset every subsequent Forgejo push fast-forwards cleanly and the
mirror job stays green with no further intervention.

## See also

- [release.md](release.md) - the release pipeline this mirror hangs off.
- [`.forgejo/workflows/mirror-to-github.yml`](../.forgejo/workflows/mirror-to-github.yml) - the job itself.

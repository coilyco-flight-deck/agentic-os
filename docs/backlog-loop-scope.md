# Backlog loop: multi-repo scope

The [backlog loop](backlog-loop.md) drives one repo's open backlog by default. A **scope** spans more than one repo so a single train of work split across repos - `ward` pushing issues down into `cli-guard`, say - drives as one loop instead of one `--repo` at a time ([agentic-os#279](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/279)).

## Spelling a scope

Pass a comma-separated set to `--repo`:

```
ward exec backlog-loop -- select --repo coilyco-flight-deck/ward,coilyco-flight-deck/cli-guard
```

One slug is a scope of one (the existing single-repo behavior, unchanged). The set is de-duped and order-preserving. Named scopes (`ward agent backlog <scope>`) graduate into ward as a first-class type; here a scope is just its repo list.

## What aggregates

The lane-level verbs span the whole set in one invocation:

- **select** refreshes every repo's ledger, then prints one combined, lane-grouped, cross-repo-ranked view (each issue shown as `<owner/name>#<num>`).
- **next** merges each repo's lane picks into one ranked list - blocked first (a human is waiting), then the cross-repo lane order (tier, then triage score, then repo, then number) - so you pull the single most-actionable issue regardless of which repo it lives in.
- **poll** reconciles every dispatched container across the scope in one pass.

## What stays per-repo

Each repo keeps its **own** durable ledger under `~/.cache/agentic-os/backlog-loop/<owner>-<name>.yaml`. The scope is a read-time aggregation, not a merged file, so issue-number collisions across repos never clash and a single-repo loop reads exactly the same ledger it always did.

Per-issue verbs (`dispatch` / `outcome` / `unblock` / `mark`) act on one issue in one repo, so they take either a bare `<num>` or an `<owner/name>#<num>` ref. A bare num resolves with no qualifier in a one-repo scope, or when exactly one repo in the scope tracks it; across a multi-repo scope where the number is ambiguous or untracked, the loop tells you to qualify it as `<owner/name>#<num>`.

```
ward exec backlog-loop -- next --lane headless                       # ranked across the scope
ward exec backlog-loop -- dispatch coilyco-flight-deck/cli-guard#12  # ref picks the repo
ward exec backlog-loop -- poll                                       # every container, one pass
```

## See also

- [backlog-loop.md](backlog-loop.md) - the loop itself, lanes, ledger, and outcome channel.
- [tooling-backlog-loop](../.agents/skills/tooling-backlog-loop/SKILL.md) - the supervisor protocol skill.

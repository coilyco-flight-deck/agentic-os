# Ward burndown policy

Ward's issue burndown stays deny-by-default until actor-aware admission lands.
Autonomous triage can only run where a repo is explicitly opted in.

## Current containment

- `burndown default=#false` is the fleet default.
- Opt-in is per repo and explicit. A small number of repos carry it, all of them unreachable for writes from the public Forgejo API.
- Public repos stay available for normal issue reporting and human triage, but they do not inherit autonomous execution.

The roster itself lives in Ward's actor-aware queue filter and the host-local
`director.default-scope`, which are the surfaces that decide admission. This doc
records the policy, not the list.

## Rollout order

1. Keep deny-by-default containment in Ward's actor-aware queue filter, with
   the candidate set selected through host-local `director.default-scope`.
2. Add a repo-level external issue-admission setting in Ward.
3. Require the setting to name the approval mode and configured automation actors.
4. Fail closed when the setting is missing or unknown.
5. Re-enable an external tracker only after Ward provenance checks and snapshot tests pass.

## Admission rule

- Externally writable from the public Forgejo API - denied, no exceptions, whoever owns the repo.
- Not externally writable - eligible for an explicit opt-in, and denied until it has one.
- Unreachable from the public API is necessary but not sufficient. Repos in that state are still denied by default, because containment tracks the trust of the issue actor rather than the reachability of the repo.
- Neither state is inherited. A repo that changes writability keeps its current admission until the opt-in is revisited deliberately.

## Acceptance trail

- The fleet docs distinguish repository-owner trust from issue-actor trust.
- Every return to autonomous burndown needs the Ward issue provenance checks and snapshot tests to pass.
- The parent program links this inventory and the staged restoration evidence.

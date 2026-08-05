# QA verification fixture

AOS binds Ward's provider-neutral fixture mode to
`coilyco-flight-deck/ward-qa-fixture` and the `qa-fixture` issue label.

The lane proves the real engineer and QA control path without
granting QA mutation authority over ordinary repositories, main branches,
merges, releases, deploys, or production targets.

## One-time Ops bootstrap

Ops creates the public fixture repository with an initialized README and adds
the public `qa-fixture` label to the `coilyco-flight-deck` organization through
the tracked bootstrap:

```bash
ward exec qa-verification-fixture -- bootstrap
```

The bootstrap is idempotent. The run entry point fails closed until both
resources exist.

This bootstrap is an operator action because repository and organization-label
creation change shared Forgejo state. The engineer role authors the binding but
does not perform that live mutation.

## Run

An authorized QA session runs:

```bash
ward exec qa-verification-fixture
```

The verb performs one bounded sequence:

1. AOSguard creates one timestamped issue and attaches `qa-fixture`,
   `headless`, and `P4`.
2. Ward proves that a non-fixture repository and a merge workflow are refused
   before launch.
3. Ward launches one fixture engineer under `remote-branch-only`.
4. The entry point waits for the deterministic `issue-N` branch.
5. Fixture QA checks out that exact branch and records its commit and verdict.
6. The entry point stops residual work, deletes the issue branch, and closes
   the fixture issue.

The cleanup trap runs on success and failure. QA may pass
`--preserve-on-failure` to retain the failed branch and issue for evidence.
Ward still stops the workload before preserving them.

## Evidence

Ward stamps fixture containers with `WARD_VERIFICATION_FIXTURE=1` and
`ward.verification-fixture=true`. The issue thread records the engineer
outcome, QA verdict, reviewed commit, and cleanup-visible terminal state.
Ward's append-only audit records each launch and cleanup command.

## Failure ownership

QA sends a product failure back to Engineer with the fixture issue and reviewed
commit. QA files an `interactive` issue for Ops when the failure is in Forgejo,
container launch, credentials, runner state, or cleanup. QA does not remediate
those live substrates inside the verification run.

## Ownership boundary

The concrete repository, label, script, image defaults, and model defaults are
AOS deployment values. Ward owns only generic admission and enforcement. See
[ward-specs.md](ward-specs.md) and Ward's
[verification fixture contract](https://github.com/coilyco-flight-deck/ward/blob/main/docs/verification-fixtures.md).

# Claude credentials and settings

A native session home is session-scoped, and Claude Code keys its macOS Keychain
credential to that home. Without a bridge the harness starts logged out on every
launch. This page records why, and what the launcher does about it.

## Why the symlink farm cannot cover it

[The Claude configuration projection](native-harness-config.md) links
`.claude.json` into the session home, so folder trust, the MCP registry, and
onboarding state all carry forward. Credentials do not travel that path. On
macOS the OAuth token lives in the login Keychain, and no file in the projected
home holds it.

Claude Code namespaces that Keychain item by a digest of `CLAUDE_CONFIG_DIR`.
The default config directory keeps the bare service name
`Claude Code-credentials`, and any other directory takes a suffix of the first
four bytes of the SHA-256 of the exact path string.

Every native session mints a fresh id, so `CLAUDE_CONFIG_DIR` differs on every
launch, which yields a service name that has never been written. The harness
reports no error. It simply asks the operator to log in, stores the result under
the session-scoped service, and abandons it when the session directory is
reaped. Repeated launches accumulate stranded Keychain items.

## What the launcher does

The launcher lends the credential in and takes it back.

At session creation, when the harness is Claude and the session has its own
home, the launcher reads the host service and writes the same secret under the
session service. The resolved session service is recorded on the lease.

At the next startup, cleanup sees the finished session, reads whatever the
session service now holds, writes it back to the host service, and deletes the
session item. The harvest happens as soon as a session is observed dead, ahead
of the worktree grace period, because the next launch needs the refreshed value
rather than the one lent out a day earlier. Deleting the session item on harvest
is what keeps orphans from accumulating.

The write-back matters because a refresh token normally rotates when it is used.
A session that never handed its token back would leave the host holding a value
that the provider has already retired.

Both directions are warnings, never launch blockers. A lost token costs one
login. A cleanup that refuses to finish costs every later launch.

## Boundaries and tradeoffs

The bridge is macOS only. Linux keeps credentials in a file inside the config
directory, which the projected home already carries, and Windows credential
storage is not wired up here.

`/usr/bin/security` accepts a secret on argv or from a terminal prompt, and a
launcher cannot drive the prompt. The token therefore crosses on argv for the
duration of one call. macOS restricts another user's argv, so the exposure is a
same-user read during that window. This is a deliberate exception to the
argv-secret rule, and it is confined to this one call.

Two live sessions that each refresh their token will each write back when they
are reaped, and the later harvest wins. The earlier session's rotation is lost,
which costs one login.

A session home that resolves to the host config directory is left alone. Lending
onto the host service would make the later harvest delete the host login.

## Settings guardrails

Back to [features-agents.md](features-agents.md).

The fleet guardrails that live in `~/.claude/settings.json`. Both are authored
here and converged by the `claude-hooks` ansible role in `infrastructure`, per
the authoring-vs-rollout rule in [AGENTS.md](../AGENTS.md).

## Fleet permission rules

`scripts/apply-base-claude-settings.py` appends to `permissions.deny` and
`permissions.allow`, never replacing either, so operator rules and the sibling
`ask` / `defaultMode` keys survive untouched and a second run reports no change.

Two shut, one open:

* **Live-infrastructure CLIs** - `gcloud`, `kubectl`, `helm`, `terraform`,
  `gsutil`, `mongosh`, `mongo`. Each mutates production or a database, so it
  belongs to an operator or a guarded `aosguard ops` verb, not a raw agent
  shell. The deny is what steers an agent to the guarded surface.
* **Harness memory directory** - `Write` and `Edit` against
  `**/.claude/projects/**/memory/**`. This is the enforcement leg of the
  no-auto-memory rule. `autoMemoryEnabled: false` stops the harness from
  writing memory files; it does not stop an agent from authoring them by hand.
* **Wildcard allow** - a single `*`. Deny outranks allow, so it widens neither
  group above and only drops the prompt on the rest. The allowlists it replaces
  bounded nothing: a denied spelling just sent an agent to a permitted one.

`effortLevel` is deliberately not a fleet key. It tunes latency and spend per
host, which makes it operator-local preference under the config-placement axes,
so it stays hand-edited and no writer owns it.

## Issue-ref Stop hook

`scripts/check-issue-refs.sh` runs as a `hooks.Stop` entry. It blocks an agent
turn whose final reply references an issue or PR as a hash-ref (`owner/repo#N`
or a bare `#NN`) instead of a fully-qualified canonical Forgejo URL, which is
ambiguous after the org migration and breaks tooling. Fenced and inline code are
exempt so the convention can be quoted, and a loop guard passes the turn on the
second stop so an unfixable message cannot wedge the session. Entry-time lines
land in `~/.claude/check-issue-refs.log`, which separates "never fired" from
"fired and passed"; `CHECK_ISSUE_REFS_LOG` overrides the path.

The script lived in `agentic-os-kai` until the `settings-shared.json` merge flow
was retired, which left it with no writer. It moved down here so the fleet
writer and the ansible role could own it (agentic-os-kai#847). The role unwires
the old bridge path before wiring this one, so hosts converged before the
retirement get re-pointed rather than left stale.

## Read-only assertion

`agentic-os-kai/scripts/up-to-date.py` asserts both guardrails are present and
reads the deny rules from `BASE_DENIED_PERMISSIONS` rather than restating them.
It never writes, so a failure means the host needs convergence.

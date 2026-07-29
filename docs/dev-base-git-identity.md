# Warded-agent git identity

Per the self-name display stamp documented in
[docs/dev-base-self-name.md](dev-base-self-name.md), a warded aos session keeps
its self-name on the status line and the session banner. Git identity is
separate: the committer NAME and EMAIL resolve to the deployment bot so Forgejo
links the commit to the coilyco-ops account instead of an example fallback.

## What runs

The Dockerfile owns `AOS_GIT_NAME` and `AOS_GIT_EMAIL` once. Every language
target writes them into Git's system config through
[`install-common.sh`](../docker/dev-base/install-common.sh), so every user
inherits the deployment identity without a runtime write. The
[`ward-shell-entrypoint.sh`](../docker/dev-base/ward-shell-entrypoint.sh) maps
the same image-owned values onto Ward's provider-neutral `WARD_GIT_*` transport
seam before Ward bootstraps the container. The baked
[`agent-name.sh`](../docker/dev-base/agent-name.sh) still
carries a `gitidentity` mode as a fallback for older or custom images, and the
policy-tier [`managed-settings.json`](../docker/dev-base/claude-managed-settings.json)
wires it as a second `SessionStart` hook, right after the self-name banner.

## Why SessionStart remains

SessionStart is the earliest the self-name banner and bot identity hook can run
with the full agent environment in place. The distinguishing `<tag>` is derived
from the `session_id`, which the entrypoint cannot know before the agent starts.
The identity hook backfills only when the system config is absent, so it
respects the Dockerfile-owned config instead of overwriting it.

## Why the bot identity is explicit

The committer identity must not drift back to ward's example bot defaults. The
image-level `AOS_GIT_NAME` and `AOS_GIT_EMAIL` config owns the deployment
identity. Ward carries those values only through its generic runtime contract.

## Scope and limits

- **Best-effort.** A git failure is swallowed so it never breaks session start.
- **all warded harnesses.** The entrypoint establishes the image-owned identity
  before any harness starts. Claude's SessionStart hook remains a fallback.
- **Dockerfile owns the baseline.** The runtime hook is fallback only.

## See also

- [docs/dev-base-self-name.md](dev-base-self-name.md) - the self-name this builds on.
- [docs/dev-base-image.md](dev-base-image.md) - the image both ride in.
- [docs/FEATURES.md](FEATURES.md) - feature inventory.

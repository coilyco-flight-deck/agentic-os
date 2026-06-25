# Warded-agent git identity

Per [agentic-os#244](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/244)
a warded aos bot stamps its [self-name](dev-base-self-name.md) as the git
author/committer **name**, so a commit records *which* agent made it instead of
a generic bot string. The commit name matches the name on the status line and in
issue signoffs.

## What runs

The baked [`agent-name.sh`](../docker/dev-base/agent-name.sh) carries a
`gitidentity` mode that runs `git config --global user.name "<self-name>"`. The
policy-tier [`managed-settings.json`](../docker/dev-base/claude-managed-settings.json)
wires it as a second `SessionStart` hook, right after the self-name banner. A
warded commit then reads `claude-linux-<host>-<tag>-she-her
<coilyco-ops@coilysiren.me>`.

## Why SessionStart, not the ward entrypoint

SessionStart is the earliest the **full** name exists. The distinguishing
`<tag>` is derived from the `session_id`, which the ward entrypoint cannot know
before the agent starts - it can only set a generic name at bring-up. The
`--global` write here wins over that `--system` `user.name`.

## Why the email is left untouched

ward sets `user.email` at `--system` to the `coilyco-ops` bot address. That
email is the **load-bearing** match Forgejo links a commit to an account (and
its avatar) on
([ward#245](https://forgejo.coilysiren.me/coilyco-flight-deck/ward/issues/245),
ward `docs/agent-attribution.md`). Swapping in a per-agent email prefix - the
literal reading of the issue title - would break that link. So `gitidentity`
writes only `user.name` and lets `user.email` fall through to the bot: a commit
is named per agent yet still account-linked, the best of both.

## Scope and limits

- **Best-effort.** A git failure is swallowed so it never breaks session start.
- **claude only today.** The stamp rides claude's policy-tier settings; other
  harnesses fall back to ward's `WARD_GIT_NAME` knob (defaulting to the bot).
  A cross-harness stamp would belong in ward's entrypoint, where every harness
  passes through.

## See also

- [docs/dev-base-self-name.md](dev-base-self-name.md) - the self-name this builds on.
- [docs/dev-base-image.md](dev-base-image.md) - the image both ride in.
- [docs/FEATURES.md](FEATURES.md) - feature inventory.

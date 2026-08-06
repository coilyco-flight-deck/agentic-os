---
doc_goal: Define role-scoped Forgejo issue-pin hydration for AOS launches.
---
# AOS issue-pin context

AOS can hydrate a bounded set of Forgejo pinned issues into launch context for
one selected role. Agent Compose receives only local files. It never performs
the Forgejo read.

## Configuration

Place the generic config at `.agents/issue-pin-context.yaml`, or point
`AOS_ISSUE_PIN_CONTEXT` at another file:

```yaml
roles:
  strats:
    forgejo:
      owner: coilysiren
      repo: inbox
      collection: pinned
      max_bytes: 24576
      freshness: 15m
      fail_closed: true
```

`base_url` defaults to `https://forgejo.coilysiren.me`. `collection` currently
supports `pinned`. Kai-specific role-to-repo selection belongs in AOSK or local
operator config, not in the AOS product default.

## Runtime

At launch, AOS reads the role config, fetches pinned issues when the cache is
missing or stale, and writes a local Markdown context file. Standalone
containers receive that file at `/run/aos/issue-pins.md`. Warded launches mount
the same file into context-bundle materialization.

The rendered context preserves pin order, canonical URL, issue number and title,
exact body text, issue `updated_at`, hydration time, source repository, and a
snapshot digest. If `max_bytes` prevents full body inclusion, metadata remains
and the body carries an explicit clipped marker.

The context is current-state evidence only. It grants no permissions, tools,
credentials, mounts, repository access, or workflow authority.

## Cache And Freshness

Snapshots live under the AOS user cache, or under `AOS_ISSUE_PIN_CACHE_DIR` when
set. A fresh verified snapshot is reused without a Forgejo request. A stale
snapshot is marked with its age when live refresh fails and `fail_closed` is
false. With `fail_closed: true`, a stale or unavailable live read stops launch.

`FORGEJO_TOKEN` or `AOS_FORGEJO_TOKEN` may authenticate the host-side read. The
token is never written into the snapshot, generated Markdown, context bundle, or
container mount.

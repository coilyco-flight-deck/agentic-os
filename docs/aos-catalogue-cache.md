---
doc_goal: Define the Git cache and local manifest emitted by AOS catalogue convergence.
---
# AOS catalogue cache and manifest

The `catalogues` section of
[AOS environment convergence](aos-convergence.md) turns remote Git sources
into verified local roots. Agent Compose consumes the result without network
access or cache ownership.

## Locators

Each source is a scalar locator selecting a repository, optional path, and
revision:

```text
owner/repo/path@ref
https://example.test/owner/repo.git/path@ref
ssh://git@example.test/owner/repo.git/path@ref
```

A bare `owner/repo` uses GitHub. Locators without a path use
`.agents/skills`. Embedded HTTP credentials are rejected. Authentication
remains Git's concern and is never copied into the manifest.

## Cache behavior

AOS keeps one locked mirror and detached worktree per normalized source under
`state_dir/cache/catalogues`. The default freshness window is ten minutes.
Mutable stale refs refresh with `git remote update --prune`. A full commit SHA
already present in the mirror needs no network refresh.

First-use failures stop convergence. When a stale refresh fails, AOS reuses
the last checkout only when that checkout and catalogue directory remain
valid. The command reports this offline fallback as a warning.

`aos converge --check` never fetches or writes. A stale mutable ref, missing
checkout, or mismatched commit reports drift. An available immutable commit
remains current regardless of cache age.

## Manifest

The emitted JSON uses the stable `aos.catalogues.v1` format. Entries preserve
declaration order because downstream precedence can depend on it:

```json
{
  "format": "aos.catalogues.v1",
  "catalogues": [
    {
      "source": "owner/repo/.agents/skills@main",
      "path": "/verified/local/root",
      "commit": "0123456789abcdef"
    }
  ]
}
```

Consumers validate `format`, preserve array order, and read `path` as the
catalogue root. `source` and `commit` make the input auditable without
exposing credentials. The manifest is written atomically only after every
configured source resolves.

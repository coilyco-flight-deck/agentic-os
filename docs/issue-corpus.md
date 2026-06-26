# Issue-corpus discovery index

A git-mirrored, greppable index of the Forgejo issue corpus, so a warded
container can answer "which issue *anywhere* mentions this phrase" offline
(agentic-os#297). It is a **discovery index, not a source of truth**: grep it to
locate an issue, then confirm live state with `ward ops forgejo issue view`.

## The gap it closes

A critical fact lived in a Forgejo issue and could not be found, because
`ward ops forgejo issue list-all` only filters titles/labels and reads one issue
at a time. There was no way to grep every body and comment across every repo. The
renderer makes the corpus just another git mirror, hydrated into containers by the
same warm-cache path that seeds `/substrate/<name>`.

## What renders

- **Source set** - every repo in [`scripts/issue-corpus-repos.txt`](../scripts/issue-corpus-repos.txt),
  open AND closed issues, bodies and every comment. The needle could live in a
  closed issue. The list is a small config, distinct from the public image seed
  (`docker/dev-base/substrate-image-repos.txt`): it adds the private
  `coilysiren/inbox`, which must never land in the public substrate image.
- **Layout** - `<owner>/<name>/<index>-<slug>.md`, one file per issue, plus
  `manifest.json` at the mirror root.
- **Header** - repo, issue number, state, title, author, labels, source
  `updated_at`, this render's `rendered-at`, and the index disclaimer pointing
  back at `ward ops forgejo issue view <owner> <name> <N>`. Then the body and the
  full comment thread.

## How it runs

The render+scan logic is [`scripts/render-issue-corpus.py`](../scripts/render-issue-corpus.py)
(`ward exec render-issue-corpus -- --mirror-dir <clone>`). It is hermetic and
git-free so it unit-tests cleanly; the hourly cron
[`.forgejo/workflows/issue-corpus.yml`](../.forgejo/workflows/issue-corpus.yml)
owns the git side (clone the private mirror, run the renderer, commit, push), the
same split as `dep-bump.yml`.

- **Token boundary** - all Forgejo I/O routes through `ward ops forgejo`
  (ward-kdl, coilyco-ops from SSM), so the script holds no `FORGEJO_TOKEN`, like
  `goose-triage.py`.
- **Incremental** - `list-all` returns each issue's `updated_at` cheaply; an issue
  unchanged since the last run (recorded in `manifest.json`) is skipped without
  the per-issue comment fetch. `--force` re-renders everything. A title edit moves
  the slug path and the stale file is removed.
- **Privacy** - the mirror is private (it carries `coilysiren/inbox`). The
  renderer runs trufflehog over the corpus and exits non-zero on any finding (or a
  missing scanner) **before** the cron pushes, so a leaky corpus never lands.
  `--no-scan` is for local dry runs only.

## Rollout (not authored here)

Per the AGENTS.md authoring-vs-rollout split, this repo authors the renderer and
the cron. These prerequisites are fleet rollout and land in
`infrastructure/ansible`, not here:

- the private mirror repo (default `coilysiren/issue-corpus`) and its
  `ISSUE_CORPUS_PUSH_TOKEN` workflow secret,
- the `ward` binary plus AWS/SSM on the Forgejo runner (the I/O boundary),
- the container mount that hydrates this mirror into `/substrate` - a separate
  **ward** sibling issue, blocked on this one.

The cron no-ops cleanly while the push token is unset, so it does not red-fail
every hour until the rollout lands.

## Discipline

Grep finds the needle, the API confirms the live state. A snapshot must never
silently anchor a stale picture - the same anti-drift rule the no-auto-memory
doctrine encodes. Always confirm a grep hit with `ward ops forgejo issue view`.
